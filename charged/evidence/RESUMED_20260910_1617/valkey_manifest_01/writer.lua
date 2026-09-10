local req = cjson.decode(ARGV[1])
local args = {}
local function increment_decimal(v)
    assert(type(v) == 'string' and string.match(v, '^%d+$'))
    assert(#v == 1 or string.sub(v, 1, 1) ~= '0')
    local digits, carry = {}, 1
    for j=#v,1,-1 do
        local d = string.byte(v,j) - 48 + carry
        if d == 10 then d=0;carry=1 else carry=0 end
        digits[j] = string.char(48+d)
    end
    return (carry == 1 and '1' or '') .. table.concat(digits)
end
local seen = {}
for _,p in ipairs(req.updates) do
    local i = p[1]
    assert(not seen[i]); seen[i] = true
    local old = redis.call('HGET', KEYS[1], 'v:'..i)
    local blob = redis.call('HGET', KEYS[1], 'b:'..i)
    assert(type(blob) == 'string' and #p[2] == #blob)
    args[#args+1]='v:'..i; args[#args+1]=increment_decimal(old)
    args[#args+1]='b:'..i; args[#args+1]=p[2]
end
assert(#args > 0)
return redis.call('HSET', KEYS[1], unpack(args))
