local n=tonumber(ARGV[1]);assert(n and n>0)
local v,d={},{}
for i=1,n do
    v[i]=redis.call('HGET',KEYS[1],'v:'..i)
    d[i]=redis.call('HGET',KEYS[1],'d:'..i)
    assert(type(v[i])=='string' and type(d[i])=='string' and #d[i]==40)
end
local result={versions=v,digests=d};local encoded=cjson.encode(result)
local reply={3,v,d}
redis.call('SET',KEYS[2],encoded)
return reply
