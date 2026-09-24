final class UnrelatedMethods {
    static final class Helper {
        void getMethod(String name) {}
        void getField(String name) {}
        void loadClass(String name) {}
        void newInstance() {}
    }

    void exercise(boolean h) {
        Helper helper = new Helper();
        if (h) {
            helper.getMethod("not reflection");
            helper.loadClass("not a loader");
        }
        helper.getField("still not reflection");
        helper.newInstance();
    }
}
