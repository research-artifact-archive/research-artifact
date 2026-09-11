import java.nio.file.*;
import java.util.*;
public final class FilterDriver {
    public static void main(String[] args) throws Exception {
        for (String row:Files.readAllLines(Path.of(args[0]))) {
            String[] a=row.split("\t",-1);
            String id=a[0]; ResidualFilter f=null;
            List<Object> events=new ArrayList<>(); String constructorError="";
            try { f=new ResidualFilter(Json.longs(a[1]),Long.parseLong(a[2]),Long.parseLong(a[3])); }
            catch (IllegalArgumentException | ArithmeticException e) { constructorError=e.getClass().getSimpleName(); }
            if (f!=null && !a[4].equals("-")) for(String op:a[4].split(";")) {
                String[] z=op.split(":"); String code=z[0];long w=Long.parseLong(z[1]);
                var before=f.state(); Object result=null;String error="";
                try {
                    if (code.equals("Q")) result=f.permitsFresh(w);
                    else f.recordCompletion(w,code.equals("N")?null:ResidualFilter.Outcome.valueOf(code));
                } catch (IllegalArgumentException | ArithmeticException e) { error=e.getClass().getSimpleName(); }
                events.add(Json.obj("op",code,"weight",w,"before",before,"result",result,"error",error,"after",f.state()));
            }
            System.out.println(Json.encode(Json.obj("id",id,"constructorError",constructorError,"events",events,"final",f==null?null:f.state())));
        }
    }
}
