local n=tonumber(ARGV[1]);local v,d={},{}
for i=1,n do
    v[i]=redis.call('HGET',KEYS[1],'v:'..i)
    local blob=redis.call('HGET',KEYS[1],'b:'..i)
    assert(type(v[i])=='string' and type(blob)=='string')
    d[i]=redis.sha1hex(blob)
end
local result={versions=v,digests=d};local encoded=cjson.encode(result)
local reply={2,v,d}
redis.call('SET',KEYS[2],encoded)
return reply
