final class UnsupportedReceiver {
    void resolve() throws Exception {
        Class<?> owner = getClass();
        owner.getMethod("run");
    }
}
