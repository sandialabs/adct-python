# Copyright 2025 NTESS. See the top-level LICENSE.txt file for details.
#
# SPDX-License-Identifier: BSD-3-Clause
#
import array
import numpy
import adctk
#import adctk.adc_types
#import adctk.builder
#import adctk.publisher

adc_plugin_file_config = {
        "ADC_FILE_PLUGIN_DIRECTORY": "./test.outputs", 
        "ADC_FILE_PLUGIN_FILE": "out.file.log",
        "ADC_FILE_PLUGIN_APPEND": "true"
    }

file_config = { "DIRECTORY": "./test.outputs", 
        "FILE": "out.file.log",
        "APPEND": "true"
    }

# fixme: use logger

# config w/file_config and call initialize.
def test_publisher( pub: adctk.Publisher,  b: adctk.Builder) -> int :
    err = 0
    e = 0
    err = pub.config(**file_config)
    if err:
        print(f"config failed {err}")
        e += 1
    err = pub.initialize()
    if err:
        print(f"initialize failed {err}")
        e += 1
        err = 0
    err = pub.publish(b) # there should be 1 b in the output
    if err:
        print(f"publish 1 failed {err}")
        e += 1
        err = 0
    return e

def not_scalar_or_string(var):
    # returns False for numeric scalars and standard strings
    return numpy.ndim(var) > 0 and not isinstance(var, (str, bytes))

# check in builder named b for a field named NAME with value VAL and types as CPTYPE and CTYPE
def roundtrip(NAME: any, VAL: any, CPTYPE: adctk.adc_types.ScalarType, b):
    ck = b.get_value(NAME)
    print(f"DEB: {NAME} roundtrip {ck}")
    print(f"{NAME} roundtrip", end='')
    if (ck.kt != adctk.KeyType.k_value or not_scalar_or_string(ck.data) or
        ck.st != CPTYPE or ck.data != VAL):  # fixme: we want data comparison, not object ref comparison
        print(f"\nBAD", end='')
        print(f"\tkt: {ck.kt}", end='')
        print(f"\tst: {ck.st}", end='')
        if ck.data is not None:
            if not_scalar_or_string(ck.data):
                print(f"\tcount: {len(ck.data)}", end='')
            else:
                print("\tcount: 1", end='')
        else:
            print(f"\tcount: 0", end='')
        print(f"\tdata: {ck.data}")
    else:
        print(f"\tok {ck.data}")

def cmp_argv(argv, val) -> bool:
    for i in range(len(argv)):
        if argv[i] != str(val[i]):
            return True
    return False

#define ROUNDTRIP_ARRAY_STRING(NAME, VAL, COUNT, CTYPE_VAL) roundtrip_array_string<CTYPE_VAL>(NAME, VAL, COUNT, b)
def roundtrip_array_string(name, val, count, b):
    ck = b.get_value(name)
    print(f"{name} roundtrip ", end='')
    if ck.kt != adctk.adc_types.KeyType.k_value:
        print(f"\n WRONG kt")
    elif ck.st != adctk.adc_types.ScalarType.cp_cstr:
        print(f"\n WRONG st")
    elif len(ck.data) != count:
        print(f"\n WRONG: NOT len {count} - {len(ck.data)} instead")
    elif cmp_argv(ck.data, val):
        print(f"\n WRONG data", end="")
        for i in range(count):
            print(f"[{i}]:{ck.data[i]} vs {val[i]}")
    else:
        print(f" ok {ck.container}")
        return
    print("\nBAD", end='')
    print(f"\tkt: {ck.kt}", end='')
    print(f"\tst: {str(ck.st)}", end='')
    if ck.data:
        print(f"\tcount: {len(ck.data)}", end='')
        print("\tdata: ", end='')
        argv = ck.data
        for i in range(count):
            print(f"\t\t {argv[i]}", end='')
        print(f"\tdata: {ck.data}", end='')
    else:
        print("\t data: None", end='')
    print(f"\tcontainer: {ck.container}" )

def roundtrip_array_set(name, val, count, b):
    ck = b.get_value(name)
    print(f"{name} roundtrip ", end='')
    if ck.kt != adctk.adc_types.KeyType.k_value:
        print(f"\n WRONG kt")
    elif ck.st != adctk.adc_types.ScalarType.cp_cstr:
        print(f"\n WRONG st")
    elif len(ck.data) != count:
        print(f"\n WRONG: NOT len {count} - {len(ck.data)} instead")
    elif ck.data != set(val):
        print(f"\n WRONG data", end="")
        print(f"got {ck.data} expected {val}")
    else:
        print(f" ok {ck.container}")
        return
    print("\nBAD", end='')
    print(f"\tkt: {ck.kt}", end='')
    print(f"\tst: {str(ck.st)}", end='')
    if ck.data:
        print(f"\tcount: {len(ck.data)}", end='')
        print("\tdata: ", end='')
        argv = ck.data
        for i in range(count):
            print(f"\t\t {argv[i]}", end='')
        print(f"\tdata: {ck.data}", end='')
    else:
        print("\t data: None", end='')
    print(f"\tcontainer: {ck.container}" )

#define ROUNDTRIP_ARRAY(NAME, VAL, COUNT, CTYPE, CPTYPE) roundtrip_array<CTYPE>(NAME, VAL, adc:: CPTYPE, COUNT, b)

def roundtrip_array(name: str, val: any, cptype: adctk.adc_types.ScalarType, count: int, b: adctk.builder.Builder) -> None:
    ck = b.get_value(name)
    bad = False
    print(f"{name} roundtrip ", end='')
    if ck.kt != adctk.adc_types.KeyType.k_value:
        print("\n WRONG kt")
    elif ck.st != cptype:
        print(f"\n WRONG st. expected {adctk.adc_types.scalar_to_json(cptype)}, got {adctk.adc_types.scalar_to_json(ck.st)}")
    elif len(ck.data) != count:
        print(f"\n WRONG: NOT len {count}  {len(ck.data)} instead)")
    else:
        for i in range(count):
            if ck.data[i] != val[i]:
                bad = True
                print(f"\n WRONG maybe:")
                print(f"[{i}]: {ck.data[i]} vs {val[i]}")
    if not bad:
        print(" ok")
        return
    print("\nBAD", end='')
    print(f"\tkt: {ck.kt}", end='')
    print(f"\tst: {str(ck.st)}", end='')
    print(f"\tcount: {len(ck.data)}", end='')
    print(f"\tdata: {ck.data}")

def roundtrip_string(name: str, val: any, cptype: adctk.adc_types.ScalarType, b: adctk.builder.Builder) -> None:
    ck = b.get_value(name)
    print(f"{name} roundtrip ", end='')
    if (ck.kt != adctk.adc_types.KeyType.k_value):
        print("\n WRONG kt")
    elif len(ck.data) != len(val):
        print("\n WRONG count")
    elif ck.st != cptype:
        print("\n WRONG st")
    else:
        print(" ok")
        return
    print(f"{val} vs data {ck.data}", end='')
    print(f"\tkt: {ck.kt}", end='')
    print(f"\tst: {ck.st}", end='')
    if ck.data:
        print(f"\tcount: {len(ck.data)}")
        print(f"\tdata: {ck.data}")
    else:
        print(f"\tcount: 0")
        print(f"\tdata: None")

#define ROUNDTRIP_STRING(NAME, VAL, CPTYPE) roundtrip_string(NAME, VAL, adc:: CPTYPE, b)

def populate_builder(b, f):
    # lots of extra serialization to debug encoding
    b.add("bool0", False)
    roundtrip("bool0", False, adctk.adc_types.ScalarType.cp_bool, b)
    print(b.serialize())

    b.add("bool1", True)
    roundtrip("bool1", True, adctk.adc_types.ScalarType.cp_bool, b)
    ss = b.serialize()

    b.add("char1", 'A', "char")
    roundtrip("char1", 'A', adctk.adc_types.ScalarType.cp_char, b)
    c16 = '\u0041'
    b.add("c16", c16, "char16")
    roundtrip("c16", c16, adctk.adc_types.ScalarType.cp_char16, b)
    c32 = '\U0001F600'
    b.add("c32", c32, "char32")
    roundtrip("c32", c32, adctk.adc_types.ScalarType.cp_char32, b)
    ss = b.serialize()

    u8 = numpy.iinfo(numpy.int8).max
    u16 = numpy.iinfo(numpy.int16).max
    u32 = numpy.iinfo(numpy.int32).max
    u64 = numpy.iinfo(numpy.uint64).max
    b.add("u8", u8, 'uint8')
    roundtrip("u8", u8, adctk.adc_types.ScalarType.cp_uint8, b)
    b.add("u16", u16, 'uint16')
    roundtrip("u16", u16, adctk.adc_types.ScalarType.cp_uint16, b)
    b.add("u32", u32, 'uint32')
    roundtrip("u32", u32, adctk.adc_types.ScalarType.cp_uint32, b)
    b.add("u64", u64)
    roundtrip("u64", str(u64), adctk.adc_types.ScalarType.cp_number_str, b)
    ss = b.serialize()

    i8 = numpy.iinfo(numpy.int8).max // 2
    i16 = numpy.iinfo(numpy.int16).max // 2
    i32 = numpy.iinfo(numpy.int32).max // 2
    i64 = numpy.iinfo(numpy.int64).max // 2
    flt = numpy.finfo(numpy.float32).max / 2
    dbl = numpy.finfo(numpy.float64).max / 2
    b.add("i8", i8, 'int8')
    roundtrip("i8", i8, adctk.adc_types.ScalarType.cp_int8, b)
    b.add("i16", i16, 'int16')
    roundtrip("i16", i16, adctk.adc_types.ScalarType.cp_int16, b)
    b.add("i32", i32, 'int32')
    roundtrip("i32", i32, adctk.adc_types.ScalarType.cp_int32, b)
    b.add("i64", i64)
    roundtrip("i64", i64, adctk.adc_types.ScalarType.cp_int64, b)
    b.add("flt", flt, "f32")
    roundtrip("flt", flt, adctk.adc_types.ScalarType.cp_f32, b) 
    b.add("dbl", dbl)
    roundtrip("dbl", dbl, adctk.adc_types.ScalarType.cp_f64, b)
    ss = b.serialize()

    # numpy complex<single>
    fcplx = numpy.complex64(flt + 0.8j)
    # py
    dcplx = complex(dbl,dbl)

    b.add("fcplx", fcplx)
    ftest = numpy.array([flt, 0.8], dtype=numpy.float32)
    print(f"DEB: ftest {ftest}")
    roundtrip_array("fcplx", ftest, adctk.adc_types.ScalarType.cp_c_f32, 2, b)

    b.add("dcplx", dcplx)
    roundtrip_array("dcplx", [dbl, dbl], adctk.adc_types.ScalarType.cp_c_f64, 2, b)

    ss = b.serialize()

    ccppstr="ccppstr"
    b.add("ccppstr", ccppstr)
    roundtrip_string("ccppstr", ccppstr, adctk.adc_types.ScalarType.cp_cstr, b)

    cppstr="cppstr"
    b.add("cppstr", cppstr)
    roundtrip_string("cppstr", cppstr, adctk.adc_types.ScalarType.cp_cstr, b)

    cstr = "cstr_nul"
    b.add("cstr1", cstr)
    roundtrip_string("cstr1", cstr, adctk.adc_types.ScalarType.cp_cstr, b)

    jstr = "{\"a\":\"b\", \"c\":[1,2, 3]}"
    b.add_json_string("jstr1", jstr)
    roundtrip_string("jstr1", jstr, adctk.adc_types.ScalarType.cp_json_str, b)

    ystr = "---\na: b\nc: [1,2, 3]\nd:\n  e: 1\n  f: 2"
    b.add_yaml_string("ystr1", ystr)
    roundtrip_string("ystr1", ystr, adctk.adc_types.ScalarType.cp_yaml_str, b)

    xstr = "<note> <to>Tove</to> <from>Jani</from> </note>"
    b.add_xml_string("xstr1", xstr)
    roundtrip_string("xstr1", xstr, adctk.adc_types.ScalarType.cp_xml_str, b)

    nstr = "1234567890123456789012345678901234567890.123"
    b.add_number_string("number1", nstr)
    roundtrip_string("number1", nstr, adctk.adc_types.ScalarType.cp_number_str, b)
    ss = b.serialize()
    # fixme roundtrip complex
    cstrings = ["a", "B", "c2"]
    vcstrings = []
    ia = []
    fa = numpy.empty(4, dtype=numpy.float32)
    ua = numpy.empty(4, dtype=numpy.uint64)
    da = []
    for i in range(4):
        vcstrings.append(str(i))
        da.append( 3.14*i)
        ua[i] = numpy.uint64(i)
        ia.append( -i)
        fa[i] =  3.14*i *2

    match ua[0]:
        case numpy.uint64():
            print("Matched OK numpy u64")
        case _:
            print("Match FAILED numpy u64")
    print(f"DEB: format ia: {ia}")
    b.add("ia", ia)
    ss = b.serialize()
    roundtrip_array("ia", ia, adctk.adc_types.ScalarType.cp_int64, 4, b)

    print(f"DEB: format ua: {ua}")
    b.add("ua", ua)
    ss = b.serialize()
    roundtrip_array("ua", ua, adctk.adc_types.ScalarType.cp_uint64, 4, b)

    print(f"DEB: format fa: {fa}")
    b.add("fa", fa)
    ss = b.serialize()
    roundtrip_array("fa", fa, adctk.adc_types.ScalarType.cp_f32, 4, b)

    print(f"DEB: format da: {da}")
    b.add("da", da)
    ss = b.serialize()
    roundtrip_array("da", da, adctk.adc_types.ScalarType.cp_f64, 4, b)

    b.add("nulembed", array.array('b', b"a\0b"))
    roundtrip_array("nulembed", array.array('b', b"a\0b"), adctk.adc_types.ScalarType.cp_char, 3, b)

    cppstrings = ["ap", "Bp", "c2p"]
    b.add("cstrs", cstrings)
    roundtrip_array_string("cstrs", cstrings, 3, b)
    b.add("cppstrs", cppstrings)
    roundtrip_array_string("cppstrs", cppstrings, 3, b)
    b.add("vcstrs", vcstrings)
    roundtrip_array_string("vcstrs", vcstrings, 4, b)
    ss = b.serialize()

    e1="a1"; e2="a2"; e3="a3"; eb="b"; ec="c_"
    tcsv = [ e1, eb, ec ]
    tcsl = [ e2, eb, ec ]
    tcss = set([  e3, eb, ec ])
    tcsv_a = [ e1, eb, ec ]
    tcsl_a = [ e2, eb, ec ]
    tcss_a = set([ e3, eb, ec ])

    b.add("sv", tcsv)
    b.add("sl", tcsl)
    b.add("ss", tcss)
    ss = b.serialize()
    roundtrip_array_string("sv", tcsv_a, 3, b)
    roundtrip_array_string("sl", tcsl_a, 3, b)
    # the ss test depends on strcmp order of tcss to match sortedness of tcss_a
    roundtrip_array_set("ss", [ e3, eb, ec], 3, b)

    children = ( "uuid1", "uuid2", "uuid3")
    b.add_workflow_section()
    b.add_workflow_children(children)
    ss = b.serialize()

    
    # section test with host-like data treated as app data
    host = f.get_builder()
    arch = f.get_builder()
    cpu = f.get_builder()
    mem = f.get_builder()

    host.add("name","myhost")
    host.add("cluster","mycluster")
    cpu.add("processor","pentium II")
    mem.add("size", "256G")

    arch.add_section("cpu", cpu)
    arch.add_section("memory", mem)
    host.add_section("architecture",arch)
    b.add_section("host", host)
    ss = b.serialize()

    # section test with host-like data treated as standard schema data (json fields of default types), not app fields)
    host2 = dict()
    arch2 = dict()
    cpu2 = dict()
    mem2 = dict()

    host2["NAME"] = "MYHOST"
    host2["CLUSTER"] ="MYCLUSTER"
    cpu2["PROCESSOR"] = "PENTIUM ii"
    mem2["SIZE"] = "256g"
    arch2["CPU"] = cpu2
    arch2["MEMORY"] = mem2
    host2["ARCHITECTURE"] = arch2

    b.add("host2", host2)

    ss = b.serialize()
    print("-------------------------------")
    print(ss)
    print("-------------------------------")

def main() -> int:
    print(f"adc pub version: {adctk.Publisher.API_VERSION}")
    print(f"adc builder version: {adctk.Builder.API_VERSION}")
    print(f"adc factory version: {adctk.Factory.API_VERSION}")
    print(f"adc enum last: {adctk.adc_types.ScalarType.cp_last}")

    f = adctk.Factory

    b = f.get_builder()

    populate_builder(b, f)

    print("NONE TEST")
    p0 = f.get_publisher("none")
    print(test_publisher(p0, b))

    print("FILE TEST")
    p1 = f.get_publisher("file")
    print(test_publisher(p1, b))

    print("STDOUT TEST")
    p2 = f.get_publisher("stdout")
    print(test_publisher(p2, b))

#   p3 = f.get_publisher("syslog")
#   print(test_publisher(p3, b))

    print("MULTIPUB TEST")

    mp = f.get_multi_publisher()
    mp.add(p0)
    mp.add(p1)
    mp.add(p2)
#   mp.add(p3)
    mp.publish(b)
    mp.pause()
    mp.publish(b)
    mp.resume()
    mp.publish(b)
    mp.terminate()

    return 0

if __name__ == "__main__":
    main()
