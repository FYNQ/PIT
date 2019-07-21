
PLUGIN=pit_plugin.so
SOURCES=\
        pit_plugin.cc \
		$(END)

INSTALLDIR=/usr


PLUGINDIR=$(shell $(CC) -print-file-name=plugin)

CXXFLAGS=-std=gnu++11 -fPIC -Wall -g -fno-rtti -I$(PLUGINDIR)/include -l json-c
# This is a side effect of using C++11
CXXFLAGS+=-Wno-literal-suffix

LDFLAGS=
LDADD=

END=
OBJECTS=$(patsubst %.cc,%.o,$(SOURCES))

all: $(PLUGIN)

$(PLUGIN): $(OBJECTS)
	$(CXX) -shared -ljson-c -liberty $(LDFLAGS) -o $@  $+ $(LDADD)
	echo $(ARCH):$(CC) > compiled4

%.o: %.cc
	$(CXX) -c -o $@ $(CXXFLAGS) $<

PLUGINFLAG=-fplugin=./$(PLUGIN) -fplugin-arg-pit_plugin-log=/tmp/test -fplugin-arg-pit_plugin-base=/home/markus/work_ot/SIL2LinuxMP/doc/investigation/gcc_pit_plugin/gcc_plugin

CCPLUGIN=$(CC) $(PLUGINFLAG)
CXXPLUGIN=$(CXX)  $(PLUGINFLAG)

.PHONY: all clean test tests format-code

format-code:
	clang-format -i -style=file *.cc

clean:
	rm -f $(OBJECTS) $(PLUGIN)
	 @$(foreach test,$(TESTS),rm -rf tests/$(test)/output;)

test: $(PLUGIN)
	rm -rf /tmp/test/
	$(CCPLUGIN) -c test_plugin.c -o /dev/null

TESTSFLAGS = -fplugin=./$(PLUGIN) -fplugin-arg-pit_plugin-log=./tests/$@/output \
	-fplugin-arg-pit_plugin-base=./tests/$@/

TESTS = \
	global_test \
	multiple_files_test \
	ifdef_test \
	ifdef_defined_test

multiple_files_test: $(PLUGIN)
	$(CC) $(TESTSFLAGS) ./tests/$@/b.c ./tests/$@/a.c -o /dev/null

ifdef_test: $(PLUGIN)
	$(CC) $(TESTSFLAGS) ./tests/$@/main.c -o /dev/null

ifdef_defined_test: $(PLUGIN)
	$(CC) $(TESTSFLAGS) -DTEST ./tests/$@/main.c -o /dev/null

global_test: $(PLUGIN)
	$(CC) $(TESTSFLAGS) -c ./tests/$@/$@.c -o /dev/null

tests: $(TESTS)
	 @$(foreach test,$(TESTS),./plugin-tests.sh tests/$(test);)
