// Infrastructure probe only: no benchmark or solver logic.
public class PortableProcessProbe {
    public static void main(String[] args) throws Exception {
        System.out.println("ready");
        System.out.flush();
        Thread.sleep(60000);
    }
}
