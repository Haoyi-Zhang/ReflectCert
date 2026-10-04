/** Self-contained accepted-expression boundary controls. No external services. */
public final class JournalBridgeControls {
    static java.lang.Class<?> conditionalWrite(boolean h) throws Exception {
        String name = "java.lang.Object";
        String ignored = h ? (name = "java.lang.String") : (name = "java.lang.Integer");
        return java.lang.Class.forName(name);
    }
    static java.lang.Class<?> shortCircuitWrite(boolean h) throws Exception {
        boolean flag = false;
        boolean ignored = h && (flag = true);
        return java.lang.Class.forName(flag ? "java.lang.String" : "java.lang.Integer");
    }
    static java.lang.Class<?> exceptionalWrite(boolean h) throws Exception {
        String name = "java.lang.Object";
        try {
            name = "java.lang.String";
            if (h) throw new IllegalStateException("controlled");
        } catch (IllegalStateException ex) {
            name = "java.lang.Integer";
        }
        return java.lang.Class.forName(name);
    }
    public static void main(String[] args) throws Exception {
        for (boolean h : new boolean[] {false, true}) {
            System.out.println("conditional," + h + "," + conditionalWrite(h).getName());
            System.out.println("short-circuit," + h + "," + shortCircuitWrite(h).getName());
            System.out.println("exception," + h + "," + exceptionalWrite(h).getName());
        }
    }
}
