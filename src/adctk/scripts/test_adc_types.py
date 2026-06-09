# Copyright 2025 NTESS. See the top-level LICENSE.txt file for details.
#
# SPDX-License-Identifier: BSD-3-Clause
import decimal
import sys
import types
#import enum
#import collections.abc
import numpy
import adctk.adc_types

# test/debugging code
def add2(x, name, value):
    if value is None:
        return
    if isinstance(value, range):
        pass
    if type(value) == int:
        if adctk.adc_types.fits_int64(value):
            pass
        #store as cp_number_str
        pass
    if type(value) == str:
        pass # subtypes detection?
    if type(value) == bool:
        pass
    if type(value) == float:
        pass
    if type(value) == complex:
        pass
    if type(value) == decimal.Decimal:
        pass
    if type(value) in (list, tuple, set, frozenset):
        pass
    if type(value).__module__ == numpy.__name__:
        print("numpy")
        if isinstance(value, numpy.ndarray):
            print(f"class: {value.__class__.__name__}")
            print(f"type: {type(value)}")
            print(f"shape: {value.shape}")
            print(f"size: {value.itemsize}")
            print(f"dtype: {value.dtype}")
            print(f"dtypedir: {dir(value.dtype)}")
            print("")
        pass

# test/debugging code
def add(x, name, value):
    print(name)
    print(value)
    print(type(value))
    print("")

def __test_get_common_py_type(name, slt, exp_depth, exp_min, exp_max, exp_type):
    depth = 0
    maxdepth = [0]
    imin =[0]
    imax =[0]
    types = set()
    pt = adctk.adc_types.__get_common_py_type(slt, depth, maxdepth, imin, imax, types)
    if pt is None:
        print(f"{name}: type mismatch")
    else:
        print(f"{name}: containers:{types}, depth:{maxdepth[0]},"\
                "min:{imin[0]}, max:{imax[0]}, type:{pt}")

def test_tolist_odd_types():
    import pprint
    print('uint64')
    y = numpy.iinfo(numpy.uint64).max
    r = numpy.full((2,3,4), y, numpy.uint64)
    x = adctk.adc_types.get_list_format_numpy(r)
    pprint.pprint(x)

    y = complex(numpy.finfo(numpy.float32).max / 2.0,  numpy.finfo(numpy.float32).max / 4.0 )
    print(f'c_f_32{y}')
    r = numpy.full((2,3,4), y, numpy.complex64)
    x = adctk.adc_types.get_list_format_numpy(r)
    pprint.pprint(x)

    y = complex(numpy.finfo(numpy.float64).max / 2.0,  numpy.finfo(numpy.float64).max / 4.0 )
    print(f'c_f_64{y}')
    r = numpy.full((2,3,4), y, dtype=numpy.complex128)
    x = adctk.adc_types.get_list_format_numpy(r)
    pprint.pprint(x)

    # ext_str should mostly fit in float80 as well, possibly truncating mantissa
    ext_str = "1.23456789012345678901234567890123456e+4000"
    f128 = numpy.float128(ext_str)
    print(f'c_f_128{f128}')
    r = numpy.full((2,3,4), f128, dtype=numpy.complex256)
    r.imag = r.real / 2.0
    x = adctk.adc_types.get_list_format_numpy(r)
    pprint.pprint(x)

def test_get_common_py_type():
    __test_get_common_py_type("ascalar", 1,       0, 1, 1, int)
    __test_get_common_py_type("aset", {-1, 2, 3},  1, 1, 3, int)
    __test_get_common_py_type("alist", [1.0, 2.0, 3.0], 1, 0, 0, float)
    __test_get_common_py_type("atuple", (-1, 2, 3), 1, 1, 3, int)

    __test_get_common_py_type("aset2", {frozenset([-1, 2, 3]),frozenset([-3,4,5])},
                            2, 1, 5, int)
    __test_get_common_py_type("alist2", [[1, 2, 3],[6,7]], 2, 1, 7, int)
    __test_get_common_py_type("atuple2", [(-1, 2, 3),[8,-9]], 2, -9, 8, int)

    __test_get_common_py_type("badset", {1, 2, 3.0},  1, 1, 3, int)
    __test_get_common_py_type("badlist", [1, 2, 3.0], 1, 1, 3, int)
    __test_get_common_py_type("badtuple", (1, 2, 3.0), 1, 1, 3, int)

    __test_get_common_py_type("badset2", {frozenset([-1, 2, 3]),frozenset([-3,4,5.0])},
                            2, 1, 5, int)
    __test_get_common_py_type("badlist2", [[1, 2, 3],[6,7.0]], 2, 1, 7, int)
    __test_get_common_py_type("badtuple2", [(-1, 2, 3),[8,-9.0]], 2, -9, 8, int)

def main():
    y="""
str
range
dict
bytes
bytearray
"""
    print(sys.float_info)
    print(sys.int_info)
    int64_max_value = numpy.iinfo(numpy.int64).max
    print("imax")
    print(int64_max_value)
    uint64_max_value = numpy.iinfo(numpy.uint64).max
    print("umax")
    print(uint64_max_value)
    int64_min_value = numpy.iinfo(numpy.int64).min
    print("imin")
    print(int64_min_value)
    uint64_min_value = numpy.iinfo(numpy.uint64).min
    print("umin")
    print(uint64_min_value)
    add(0, "str","str")
    add(0, "list",["a",2.0,"1"])
    add(0, "tuple",("a",2.0,"1"))
    add(0, "range",(5))
    add(0, "dict",{})
    add(0, "dict2",{0:0 })
    add(0, "set",{ 1,2,3 })
    add(0, "fset", frozenset({"apple", "banana", "cherry"}) )
    add(0, "bool",True)
    add(0, "bytes", '123')
    add(0, "bytearray", b'123')
    add(0, "none", None)
    add(0, "int", 123)
    add(0, "int10", 123123123123123)
    add(0, "int20", 12312312312312312312)
    add(0, "int36", 123123123123123123121231231231231231)
    add(0, "int67", 1231231231231231231212312312312312313412312312312312312312321313213)
    add(0, "decimal", decimal.Decimal('1.2342342234324234234243242'))
    add(0, "float", 1.345)
    add(0, "floatq", 1.34512312312312312312312312312)
    add(0, "complex", complex(1.1,2.2))
    add(0, "icomplex", complex(1,2))
    zr = numpy.zeros(shape = (2,3, 9))
    add2(0,"numpy", zr)
    zr = numpy.zeros(shape = (2,3, 9), dtype=numpy.bool)
    add2(0,"numpy", zr)
    r = numpy.zeros(shape = (2,3, 9), dtype=numpy.uint64)
    add2(0,"numpy", r)
    test_get_common_py_type()
    test_tolist_odd_types()
    print("done")

if __name__ == "__main__":
    main()
