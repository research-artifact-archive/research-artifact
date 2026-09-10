-- Author application, running on an unmodified pinned Valkey server.
local req = cjson.decode(ARGV[1])
local n = #req.sizes
assert(n > 0 and req.t >= 0 and req.e >= 0)
assert(#req.versions == n and #req.digests == n)
local fields = {}
for i=1,n do fields[#fields+1] = 'v:'..i end
local current = redis.call('HMGET', KEYS[1], unpack(fields))
local dirty, mask = {}, 0
for i=1,n do
    assert(type(current[i]) == 'string')
    assert(type(req.versions[i]) == 'string')
    assert(type(req.digests[i]) == 'string' and #req.digests[i] == 40)
    if current[i] ~= req.versions[i] then
        dirty[#dirty+1] = i
        mask = mask + 2^(i-1)
    end
end
local next_e = math.min(req.ceiling, req.e + req.counts[tostring(mask)])
local action = 'a'
if req.mode == 'retry' and mask ~= 0 and req.t > 0 then action = 'r' end
if req.mode == 'compiled' then
    action = req.actions[req.t..':'..req.e..':'..mask]
    assert(action == 'a' or action == 'r')
end
assert(action ~= 'r' or req.t > 0)
if action == 'r' then
    return cjson.encode({action='r', mask=mask, dirty=dirty,
        hash_bytes=0, versions=current, next_e=next_e, next_t=req.t-1})
end
local hashes = {}
for i=1,n do hashes[i] = req.digests[i] end
local count = 0
for _,i in ipairs(dirty) do
    local blob = redis.call('HGET', KEYS[1], 'b:'..i)
    assert(type(blob) == 'string' and #blob == req.sizes[i])
    hashes[i] = redis.sha1hex(blob)
    count = count + #blob
end
local result = {versions=current, digests=hashes}
local encoded = cjson.encode(result)
local reply = cjson.encode({action='a', mask=mask, dirty=dirty,
    hash_bytes=count, versions=current, result=result, next_e=next_e})
-- Every check, transform and encoding precedes the single publication.
redis.call('SET', KEYS[2], encoded)
return reply
