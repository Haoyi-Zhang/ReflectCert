final class SupportedFinite {
    void resolve(boolean h, boolean k) throws Exception {
        String prefix = "pkg.";
        boolean chooseA = h && !k;
        String className = prefix.concat(chooseA ? "A" : "B");
        java.lang.Class<?> owner = java.lang.Class.forName(className);
        owner.getMethod(h ? "run" : "stop", String.class);
    }
}
