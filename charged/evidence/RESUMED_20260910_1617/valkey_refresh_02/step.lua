local req=cjson.decode(ARGV[1])
local before = req.measure and redis.retrysha1blocks() or 0
local n=#req.sizes
assert(n>0 and #req.versions==n and #req.digests==n and req.t>=0)
local fields={}
for i=1,n do fields[#fields+1]='v:'..i end
local current=redis.call('HMGET',KEYS[1],unpack(fields))
local dirty,mask={},0
for i=1,n do
    assert(type(current[i])=='string' and type(req.versions[i])=='string')
    assert(type(req.digests[i])=='string' and #req.digests[i]==40)
    if current[i]~=req.versions[i] then dirty[#dirty+1]=i;mask=mask+2^(i-1) end
end
local next_e=math.min(req.ceiling,req.e+req.counts[tostring(mask)])
local action='a'
if req.mode=='retry' and mask~=0 and req.t>0 then action='r' end
if req.mode=='compiled' then
    action=req.actions[req.t..':'..req.e..':'..mask]
    assert(action=='a' or action=='r')
end
assert(action~='r' or req.t>0)
if action=='r' then
    local refresh={}
    for _,i in ipairs(dirty) do
        local blob=redis.call('HGET',KEYS[1],'b:'..i)
        assert(type(blob)=='string' and #blob==req.sizes[i])
        refresh[#refresh+1]={i,blob}
    end
    return cjson.encode({action='r',mask=mask,dirty=dirty,versions=current,
        refresh=refresh,hash_bytes=0,hash_blocks=req.measure and redis.retrysha1blocks()-before or -1,
        next_e=next_e,next_t=req.t-1})
end
local hashes={}
for i=1,n do hashes[i]=req.digests[i] end
local bytes=0
for _,i in ipairs(dirty) do
    local blob=redis.call('HGET',KEYS[1],'b:'..i)
    assert(type(blob)=='string' and #blob==req.sizes[i])
    hashes[i]=redis.sha1hex(blob);bytes=bytes+#blob
end
local result={versions=current,digests=hashes}
local encoded=cjson.encode(result)
local reply=cjson.encode({action='a',mask=mask,dirty=dirty,versions=current,
    result=result,hash_bytes=bytes,hash_blocks=req.measure and redis.retrysha1blocks()-before or -1,next_e=next_e})
redis.call('SET',KEYS[2],encoded)
return reply
