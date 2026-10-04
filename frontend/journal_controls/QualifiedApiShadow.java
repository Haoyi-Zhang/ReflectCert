/** Qualified spelling alone is not symbol attribution. */
public final class QualifiedApiShadow {
    static final class Factory {
        java.lang.Class<?> forName(String ignored) { return java.lang.String.class; }
    }
    static final class Namespace { final Factory Class = new Factory(); }
    static final class Root { final Namespace lang = new Namespace(); }
    static java.lang.Class<?> qualifiedShadow(Root java) {
        return java.lang.Class.forName("ignored");
    }
    public static void main(String[] args) {
        System.out.println("qualified-shadow," + qualifiedShadow(new Root()).getName());
    }
}
