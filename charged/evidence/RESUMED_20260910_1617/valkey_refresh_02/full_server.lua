local n=tonumber(ARGV[1]);local measure=ARGV[2]=='1'
local before=measure and redis.retrysha1blocks() or 0
local v,d={},{};local bytes=0
for i=1,n do
    v[i]=redis.call('HGET',KEYS[1],'v:'..i)
    local blob=redis.call('HGET',KEYS[1],'b:'..i)
    assert(type(v[i])=='string' and type(blob)=='string')
    d[i]=redis.sha1hex(blob);bytes=bytes+#blob
end
local result={versions=v,digests=d};local encoded=cjson.encode(result)
local reply=cjson.encode({action='direct',result=result,hash_bytes=bytes,
    hash_blocks=measure and redis.retrysha1blocks()-before or -1})
redis.call('SET',KEYS[2],encoded)
return reply
