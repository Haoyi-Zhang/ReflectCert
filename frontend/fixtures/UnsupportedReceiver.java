final class UnsupportedReceiver {
    void resolve() throws Exception {
        java.lang.Class<?> owner = getClass();
        owner.getMethod("run");
    }
}
