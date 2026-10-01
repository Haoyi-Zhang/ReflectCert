final class UnsupportedParameter {
    void resolve(Class<?> parameterType) throws Exception {
        java.lang.Class<?> owner = java.lang.Class.forName("pkg.A");
        owner.getMethod("run", parameterType);
    }
}
