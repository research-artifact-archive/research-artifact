local mode=ARGV[1]
assert(mode=='base' or mode=='maintained')
local i=ARGV[2]
local payload=ARGV[3]
local version=redis.call('HGET',KEYS[1],'v:'..i)
local old=redis.call('HGET',KEYS[1],'b:'..i)
assert(type(version)=='string' and string.match(version,'^%d+$'))
assert(#version==1 or string.sub(version,1,1)~='0')
assert(type(old)=='string' and #payload==#old)
local digits,carry={},1
for j=#version,1,-1 do
    local d=string.byte(version,j)-48+carry
    if d==10 then d=0;carry=1 else carry=0 end
    digits[j]=string.char(48+d)
end
local nextv=(carry==1 and '1' or '')..table.concat(digits)
local fields={'v:'..i,nextv,'b:'..i,payload}
if mode=='maintained' then
    assert(type(ARGV[4])=='string' and #ARGV[4]==40)
    fields[#fields+1]='d:'..i;fields[#fields+1]=ARGV[4]
end
redis.call('HSET',KEYS[1],unpack(fields))
return nextv
