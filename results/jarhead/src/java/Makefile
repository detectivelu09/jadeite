include deps
#LLWEB_JAR=../../../browser/build/llweb.jar
#LLWEB_LIBS=../../../browser/lib/commons-logging-1.1.1.jar

all: johannesapplet.jar jarhead-tracer.jar

johannesapplet.jar: wepawetng/jarhead/JohannesAppletPlugin.java
	test -d build || mkdir build
#	svn export --force META-INF.tmpl META-INF
	javac -cp .:./build:$(LLWEB_JAR):$(LLWEB_LIBS) -d build wepawetng/jarhead/*.java
	jar -cvf appletanalysis.jar META-INF -C build/ .

jarhead-tracer.jar:
	test -d build-tracer || mkdir build-tracer
	javac -cp .:../../deps/asm-3.3.1.jar:../../deps/asm-analysis-3.3.1.jar:../../deps/asm-commons-3.3.1.jar:../../deps/asm-tree-3.3.1.jar: -d build-tracer -g wepawetng/jarhead/tracer/*.java 
	jar -cvf jarhead-tracer.jar -C build-tracer/ .

clean:
	$(RM) -r build build-tracer appletanalysis.jar jarhead-tracer.jar
#	$(RM) -rf META-INF

.PHONY: clean
