import java.util.*;
final class Json {
    static Map<String,Object> obj(Object... pairs) {
        Map<String,Object> out = new LinkedHashMap<>();
        for (int i=0;i<pairs.length;i+=2) out.put((String)pairs[i],pairs[i+1]);
        return out;
    }
    static String encode(Object x) {
        if (x==null) return "null";
        if (x instanceof String s) return "\""+s.replace("\\","\\\\").replace("\"","\\\"").replace("\n","\\n").replace("\r","\\r").replace("\t","\\t")+"\"";
        if (x instanceof Number || x instanceof Boolean) return x.toString();
        if (x instanceof ResidualFilter.State s) return encode(obj("k",s.k(),"ell",s.ell(),"topSum",s.topSum(),"completed",s.completed(),"kth",s.kth()));
        if (x instanceof Map<?,?> m) {
            List<String> out=new ArrayList<>();
            for (var e:m.entrySet()) out.add(encode(e.getKey())+":"+encode(e.getValue()));
            return "{"+String.join(",",out)+"}";
        }
        if (x instanceof Iterable<?> xs) {
            List<String> out=new ArrayList<>(); for(Object y:xs) out.add(encode(y));
            return "["+String.join(",",out)+"]";
        }
        if (x instanceof long[] a) return Arrays.toString(a);
        if (x instanceof int[] a) return Arrays.toString(a);
        throw new IllegalArgumentException("unserializable "+x.getClass());
    }
    static long[] longs(String s) { return s.equals("-") ? new long[0] : Arrays.stream(s.split(",")).mapToLong(Long::parseLong).toArray(); }
    static int[] ints(String s) { return s.equals("-") ? new int[0] : Arrays.stream(s.split(",")).mapToInt(Integer::parseInt).toArray(); }
}
