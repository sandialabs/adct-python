# Copyright 2025 NTESS. See the top-level LICENSE.txt file for details.
#
# SPDX-License-Identifier: BSD-3-Clause
import decimal
import sys
import types
import enum
import collections.abc
import array
import numpy


# \addtogroup API
# @{
#


## @brief Set to 1 if 8/16 bit float types for gpus are supported.
# ADC_SUPPORT_GPU_FLOATS should be defined by build-time configuration
ADC_SUPPORT_GPU_FLOATS = 0

## @brief Set to 1 if 80 bit floats for cpus are supported.
# ADC_SUPPORT_EXTENDED_FLOATS should be defined by build-time configuration
ADC_SUPPORT_EXTENDED_FLOATS = 1

## @brief Set to 1 if 128 bit floats for cpus are supported.
# ADC_SUPPORT_QUAD_FLOATS should be defined by build-time configuration
ADC_SUPPORT_QUAD_FLOATS = 0

class ScalarType(enum.IntEnum):
    # pylint: disable=C0103
    """! @brief field types for scientific data encode/decode with json.

    Bit precision and plain vs specialized strings are preserved
    when data is tagged following this enum.
    The add() function on the Builder automatically tags with this.
    """
    cp_none = 0
    cp_bool = 1     ##!< bool (true/false,1/0)
    cp_char = 2	##!< char (8 bit signed)
    cp_char16 = 3	##!< char16_t
    cp_char32 = 4	##!< char32_t
    #/ string is problematic. For embedded nul data or utf-8, use array of char8
    cp_cstr = 5	##!< c null-terminated string
    cp_json_str = 6	##!< c null-terminated string that contains valid json
    cp_yaml_str = 7 ##!< c null-terminated string that contains valid yaml
    cp_xml_str = 8  ##!< c null-terminated string that contains valid xml
    cp_json = 9	##!< json value (object, list, etc)
    cp_path = 10    ##!< c null-terminated string which names a file-system path
    cp_number_str = 11	##!< c string containing an exact decimal representation of any precision
    #/ unsigned int types
    cp_uint8 = 12	##!< uint8_t
    cp_uint16 = 13	##!< uint16_t
    cp_uint32 = 14	##!< uint32_t
    cp_uint64 = 15	##!< uint64_t
    #/ signed int
    cp_int8 = 16	##!< int8_t
    cp_int16 = 17	##!< int16_t
    cp_int32 = 18	##!< int32_t
    cp_int64 = 19	##!< int64_t
    #/ float
    cp_f32 = 20	##!< 32 bit float
    cp_f64 = 21	##!< 64 bit float
    cp_f80 = 22	##!< 80 bit float; requires ADC_SUPPORT_EXTENDED_FLOATS support
    cp_f128 = 23	##!< 128 bit float; requires ADC_SUPPORT_QUAD_FLOATS support
    #/ mini float types
    cp_f8_e4m3 = 24   ##!< 8 bit float (3 mantissa, 4 exponent); requires ADC_SUPPORT_GPU_FLOATS
    cp_f8_e5m2 = 25	  ##!< 8 bit float (2 mantissa, 5 exponent); requires ADC_SUPPORT_GPU_FLOATS
    cp_f16_e5m10 = 26 ##!< 16 bit float (10 mantissa, 5 exponent); requires ADC_SUPPORT_GPU_FLOATS
    cp_f16_e8m7 = 27  ##!< 16 bit bfloat (7 mantissa, 8 exponent); requires ADC_SUPPORT_GPU_FLOATS
    #/ complex float types
    cp_c_f32 = 28	##!< complex<float>
    cp_c_f64 = 29	##!< complex<double>
    cp_c_f80 = 30	##!< complex<extended>; requires ADC_SUPPORT_EXTENDED_FLOATS support
    cp_c_f128 = 31	##!< complex<quad>; requires ADC_SUPPORT_QUAD_FLOATS support
    #/ time types
    cp_timespec = 32 ##!< (second, nanosecond) as int64_t, int64_t pair from clock_gettime
    cp_timeval = 33	 ##!< gettimeofday struct timeval (second, microsecond) as int64_t pair
    cp_epoch = 34    ##!< time(NULL) seconds since the epoch (UNIX) as int64_t
    cp_mime = 35    ##!< time(NULL) seconds since the epoch (UNIX) as int64_t
    #/ reserved but not yet supported
    cp_char8 = 36       ##!< unsigned 8-bit char; reserved
    #/ end mark ; may be larger when enum is expanded
    cp_last = 37

def is_string_type(st: ScalarType) -> bool:
    """! return True if st is of the single string subclassifications"""
    if st in ( ScalarType.cp_cstr,
            ScalarType.cp_json_str,
            ScalarType.cp_yaml_str,
            ScalarType.cp_xml_str,
            ScalarType.cp_path):
        return True
    return False

def scalar_to_json(st: ScalarType, array_type=False) -> str:
    """Convert ScalarType to json type string used in add functions"""
    r = st.name[3:]
    if array_type:
        r = f"array_{r}"
    ### print(f"DEB: scalar_to_json returning {r} from {st.name}")
    return r

def scalar_from_json(name: str, strict=False):
    """! convert json type string used in add functions to ScalarType

    @param name convert json scalar type label to enum.
    @param strict if True, raises an exception when name is invalid
    array_* type prefix is stripped, if present in name.
    """
    if name.startswith("array_"):
        name = name[6:]
    if strict:
        return ScalarType.__members__["cp_"+name]
    try:
        x = ScalarType.__members__["cp_"+name]
    except:
        x = ScalarType.cp_none
    ### print(f"DEB: scalar_from_json returns {x}")
    return x

# mapping of numpy types to adc type.
# notes:
# - numpy 2.3 and older do not support precision higher than c long double (64 or 80bit)
# - currently this assumes an x86_64 or similar environment for int sizing (32 bit
#   platforms/build need to be detected and supported)
# - datetime64 and deltatime from numpy are not supported yet. fixme
__scalar_from_numpy = {
            numpy.dtype('bool'): ScalarType.cp_bool,
            numpy.dtype('intp'): ScalarType.cp_int64,
            numpy.dtype('int8'): ScalarType.cp_int8,
            numpy.dtype('int16'): ScalarType.cp_int16,
            numpy.dtype('int32'): ScalarType.cp_int32,
            numpy.dtype('int64'): ScalarType.cp_int64,
            numpy.dtype('uint8'): ScalarType.cp_uint8,
            numpy.dtype('uint16'): ScalarType.cp_uint16,
            numpy.dtype('ushort'): ScalarType.cp_uint16,
            numpy.dtype('uint32'): ScalarType.cp_uint32,
            numpy.dtype('uintc'): ScalarType.cp_uint32,
            numpy.dtype('uint64'): ScalarType.cp_uint64,
            numpy.dtype('uint'): ScalarType.cp_uint64,
            numpy.dtype('half'): ScalarType.cp_f16_e5m10,
            numpy.dtype('float16'): ScalarType.cp_f16_e5m10,
            numpy.dtype('single'): ScalarType.cp_f32,
            numpy.dtype('float32'): ScalarType.cp_f32,
            numpy.dtype('double'): ScalarType.cp_f64,
            numpy.dtype('float64'): ScalarType.cp_f64,
            numpy.dtype('longdouble'): ScalarType.cp_f80,
            # we hope in future this needs to be fixed after numpy expands
            numpy.dtype('float128'): ScalarType.cp_f80,
            numpy.dtype('complex64'): ScalarType.cp_c_f32,
            numpy.dtype('complex128'): ScalarType.cp_c_f64,
            numpy.dtype('str_'): ScalarType.cp_cstr,
            numpy.dtype('bytes_'): ScalarType.cp_char
    }

## @brief return True if py native representation of array
# dtype values is roundtrip-able.
def __py_json_numpy_ok(a):
    if 'conditional' not in __numpy_py_equivalent:
        __numpy_py_equivalent.append('conditional')
        # we may have to fix this for 32-bit pythons
    if a.dtype in __numpy_py_equivalent:
        return True
    return False


# uint, intp, uintc types all map to uint64 on 64bit machines
# we may have to fix this for 32-bit pythons/hardware if we
# ever support 32-bit pythons
__numpy_py_equivalent = [
        numpy.dtype('bool'),
        numpy.dtype('int8'),
        numpy.dtype('int16'),
        numpy.dtype('int32'),
        numpy.dtype('int64'),
        numpy.dtype('uint8'),
        numpy.dtype('uint16'),
        numpy.dtype('ushort'),
        numpy.dtype('uint32'),
        numpy.dtype('half'),
        numpy.dtype('float16'),
        numpy.dtype('single'),
        numpy.dtype('float32'),
        numpy.dtype('double'),
        numpy.dtype('float64'),
        numpy.dtype('str_'),
        numpy.dtype('bytes_')
    ]

def __scalar_from_numpy_conditional():
    """define the scalar mappings for numpy types that may be conditionally defined by numpy"""
    if 'conditional' in __scalar_from_numpy:
        return
    __scalar_from_numpy['conditional'] = True
    if hasattr(numpy, 'float96'):
        # hope this needs to be updated in future numpy
        __scalar_from_numpy[numpy.dtype('float96')] = ScalarType.cp_f80
    if hasattr(numpy, 'complex192'):
        # hope this needs to be updated in future numpy
        __scalar_from_numpy[numpy.dtype('complex192')] = ScalarType.cp_c_f80
    if hasattr(numpy, 'complex256'):
        # hope this needs to be updated in future numpy
        __scalar_from_numpy[numpy.dtype('complex256')] = ScalarType.cp_c_f80
    if hasattr(numpy, 'ulong'):
        __scalar_from_numpy[numpy.dtype('ulong')] = ScalarType.cp_uint64

def scalar_from_numpy(dt: numpy.dtype):
    """! convert numpy dtype to adc scalar type
    - numpy 2.3 and older do not support precision higher than c long double (64 or 80bit)
    - currently this assumes an x86_64 or similar environment for int sizing
    - 32 bit platforms/builds may need to be detected and supported, if they still exist
    """
    __scalar_from_numpy_conditional()
    if dt in __scalar_from_numpy:
        return __scalar_from_numpy[dt]
    ### print(dt)
    ### print(dir(dt))
    ### print(dt.__class__.__name__)
    raise ValueError("unknown numpy type mapping")

def get_common_scalar(slt: list|tuple|collections.abc.Set, depth: int,
                    maxdepth: list[int]) -> ScalarType:
    """! @brief get the common scalar type from a possibly nested tuple/set/list

     @param slt data nest with single scalar type at the leaf locations.
     @param depth current recursion depth, 0 at the application level.
     @param maxdepth is a one-element array output argument.
     """
    imin =[0]
    imax =[0]
    dtypes = set()
    pt = __get_common_py_type(slt, depth, maxdepth, imin, imax, dtypes)
    if pt is None:
        return ScalarType.cp_none
    if pt == int:
        if fits_int64(imin[0]) and fits_int64(imax[0]):
            return ScalarType.cp_int64
        return ScalarType.cp_number_str
    return type_to_scalar(pt, next(iter(slt)))

# pylint: disable-next=R0917,R0913,R0912
def __get_common_py_type(slt: list|tuple|collections.abc.Set, depth: int,
                        maxdepth: list[int], imin: list[int], imax: list[int], dtypes: set[str]):
    """We collect the common type, max depth, and largest int value (if int) among
    nested number structures. Int range discovery is to determine if number_string must be used"""
    if slt is None:
        return None
    t0 = None
    if isinstance(slt, list|tuple|collections.abc.Set):
        dtypes.add(type(slt))
        depth += 1
        if depth > maxdepth[0]:
            maxdepth[0] = depth
    else:
        if isinstance (slt, int):
            if slt > imax[0]:
                imax[0] = slt
            if slt < imin[0]:
                imin[0] = slt
        return type(slt)
    for i in slt:
        if isinstance(i, list|tuple|collections.abc.Set):
            it = __get_common_py_type(i, depth, maxdepth, imin, imax, dtypes)
            if t0 is None:
                t0 = it
                continue
            if t0 == it:
                if isinstance (i, int):
                    if i > imax[0]:
                        imax[0] = i
                    if i < imin[0]:
                        imin[0] = i
                continue
            return None
        if t0 is None:
            t0 = type(i)
            if isinstance (i, int):
                if i > imax[0]:
                    imax[0] = i
                if i < imin[0]:
                    imin[0] = i
        else:
            if t0 != type(i):
                return None
            if isinstance (i, int):
                if i > imax[0]:
                    imax[0] = i
                if i < imin[0]:
                    imin[0] = i
    return t0

def forsplitcomplex(a: numpy.ndarray) -> numpy.ndarray:
    """Convert a numpy array of fortran complex to a flat array of real pairs"""
    t = a.real.dtype
    c = numpy.ravel(a, order='F')
    top = 2*c.size
    r = numpy.ndarray((top), dtype=t)
    for i in range(0,c.size):
        r[2*i] = c[i].real
        r[2*i+1] = c[i].imag
    return r

def csplitcomplex(a: numpy.ndarray) -> numpy.ndarray:
    """Convert a numpy array of complex to a flat array of real pairs"""
    t = a.real.dtype
    c = numpy.ravel(a)
    top = 2*c.size
    r = numpy.ndarray((top), dtype=t)
    for i in range(0,c.size):
        r[2*i] = c[i].real
        r[2*i+1] = c[i].imag
    return r

# pylint: disable-next=too-many-return-statements
def get_list_format_numpy(a: numpy.ndarray):
    """! @brief build a nested list out of numpy array, accounting for
    int must fit in int64 or be string encoded and accounting for
    complex numbers.
    """
    if a is None:
        return None
    if __py_json_numpy_ok(a):
        ### print(f"PY_OK_FMT {a.dtype}")
        return numpy.ravel(a).tolist()
    # cp_uint64 cp_c_f32 cp_c_f64 cp_c_f80 cp_c_f128
    if a.dtype == numpy.dtype('uint64'):
        a_copy = a.astype(numpy.str_)
        return numpy.ravel(a_copy).tolist()
    if a.dtype == numpy.dtype('complex64'):
        if a.flags['F_CONTIGUOUS']:
            r_view = forsplitcomplex(a)
            return r_view.tolist()
        r_view = csplitcomplex(a)
        return r_view.tolist()
    if a.dtype == numpy.dtype('complex128'):
        if a.flags['F_CONTIGUOUS']:
            r_view = forsplitcomplex(a)
            return r_view.tolist()
        r_view = csplitcomplex(a)
        return r_view.tolist()
    if a.dtype == numpy.dtype('complex256'):
        if a.flags['F_CONTIGUOUS']:
            r_view = forsplitcomplex(a)
            a_copy = r_view.astype(numpy.str_)
            return a_copy.tolist()
        r_view = csplitcomplex(a)
        a_copy = r_view.astype(numpy.str_)
        return a_copy.tolist()
    return ["NOT_YET_SUPPORTED(numpy array):"+a.dtype.name]

def get_list_format(slt: list|tuple|collections.abc.Set|numpy.ndarray, st: ScalarType = None):
    """! @brief build a nested list out of homogeneous python or numpy nest"""
    if slt is None:
        return None
    if isinstance(slt, numpy.ndarray):
        return get_list_format_numpy(slt)
    result = []
    for i in slt:
        if isinstance(i, list|tuple|collections.abc.Set):
            it = get_list_format(i, st)
        else:
            # fixme: it = pyval(py_or_numpy). is there a numpy func for this
            match st:
                case ScalarType.cp_uint64:
                    it = str(int(i))
                case ScalarType.cp_number_str:
                    it = i
                case _:
                    it = i
                    ### print(f"DEB: appending {it}")
        result.append(it)
    return result

def typecode_to_scalar(v: array.array):
    tc = v.typecode
    match tc:
        case 'b':
            return ScalarType.cp_char
        case 'B':
            return ScalarType.cp_char8
        case 'u':
            if v.itemsize == 4:
                return ScalarType.cp_char32
            return ScalarType.cp_char16
        case 'w':
            return ScalarType.cp_char32
        case 'h':
            if v.itemsize == 2:
                return ScalarType.cp_int16
            return ScalarType.cp_int32
        case 'H':
            if v.itemsize == 2:
                return ScalarType.cp_uint16
            return ScalarType.cp_uint32
        case 'i':
            if v.itemsize == 2:
                return ScalarType.cp_int16
            return ScalarType.cp_int32
        case 'I':
            if v.itemsize == 2:
                return ScalarType.cp_uint16
            return ScalarType.cp_uint32
        case 'l':
            if v.itemsize == 4:
                return ScalarType.cp_int32
            return ScalarType.cp_int64
        case 'L':
            if v.itemsize == 4:
                return ScalarType.cp_uint32
            return ScalarType.cp_uint64
        case 'q':
            if v.itemsize == 8:
                return ScalarType.cp_int64
            return ScalarType.cp_number_str
        case 'Q':
            if v.itemsize == 8:
                return ScalarType.cp_uint64
            return ScalarType.cp_number_str
        case 'f':
            if v.itemsize == 4:
                return ScalarType.cp_f32
            return ScalarType.cp_f64
        case 'd':
            if v.itemsize == 8:
                return ScalarType.cp_f64
            return ScalarType.cp_number_str

# pylint: disable-next=too-many-return-statements,too-many-branches
def type_to_scalar(t: type, value=None):
    """! @brief convert python type to ScalarType
    numpy array types are supported if value is given.
    int type is supported only if a value is given.
    Semantic variations on string content are all mapped to cp_cstr.
    """
    if t is None:
        return ScalarType.cp_none
    if t == int:
        if value is None:
            raise ValueError("type_to_scalar(int) needs value argument")
        if fits_int64(value):
            return ScalarType.cp_int64
        return ScalarType.cp_number_str
    if t == str:
        return ScalarType.cp_cstr
    if t == bool:
        ### print("type_to_scalar returning cp_bool")
        return ScalarType.cp_bool
    if t == float:
        return ScalarType.cp_f64
    if t == complex:
        return ScalarType.cp_c_f64
    if t == decimal.Decimal:
        return ScalarType.cp_number_str
    if t in (list, tuple, collections.abc.Set):
        if not value:
            raise ValueError("type_to_scalar needs value argument for list/set/tuple")
        md = [0]
        return get_common_scalar(value, 0, md )
    if t == numpy.ndarray and not value:
        raise ValueError("type_to_scalar needs value argument")
    if value is not None and type(value).__module__ == numpy.__name__:
        if isinstance(value, numpy.ndarray):
            return scalar_from_numpy(value.dtype)
            # print(value.shape)
            # print(value.itemsize)
            # print(value.dtype)
        ### print(f"DEB: type_to_scalar: value {value}, type {type(value)}")
        match value:
            case numpy.float64() | numpy.float32() | numpy.float16() | \
                 numpy.int64() | numpy.int32() | numpy.int16() | numpy.int8() | \
                 numpy.uint32() | numpy.uint16() | numpy.uint8() |numpy.bool() | \
                 numpy.str_() | numpy.bytes_() | \
                 numpy.uint64() | \
                 numpy.complex64() | numpy.complex128() | \
                 numpy.complex192() | numpy.complex256():
                return scalar_from_numpy(value.dtype)
    return ScalarType.cp_none

# pylint: too-few-public-methods
class KeyType(enum.IntEnum):
    """! The builder type (section or map value) or unknown"""
    # pylint: disable=C0103
    k_none = 0
    k_section = 1
    k_value = 2

# pylint: disable-next=too-few-public-methods
class Field:
    """! Field details indicate how to handle a data returned from builder lookups.
         The data element object type will be a list or scalar; conversion back to
         python native types is up to the caller, following the hints included in
         data (if it represents a numpy array): order, shape, and major will be present.
    """
    def __init__(self):
        self.kt: KeyType = KeyType.k_none          # //!< kind of data associated with the query
        self.st: ScalarType = ScalarType.cp_none   # //!< scalar type of the data as published,
        self.container: str = None                 # //!< name of the adc container variety given, e.g. vector or numpy
        self.python: str = None                    # //!< name of the python object type, if present
        self.data: any = None                      #
    def __str__(self):
        return f"kt:{self.kt}, st:{self.st}, container:{self.container}, data:{self.data}"
    def __repr__(self):
        return f"kt:{self.kt}, st:{self.st}, container:{self.container}, data:{self.data}"

def fits_int64(v: int) -> bool:
    """! @return True if v can be stored as json signed int 64 bit"""
    if v is not None and type(v) == int:
        if -9223372036854775808 <= v <= 9223372036854775807:
            return True
        return False
    raise ValueError("argument must be int")

def fits_uint64(v: int) -> bool:
    """! @return True if v can be stored as json unsigned int 64 bit"""
    if v is not None and type(v) == int:
        if 0 <= v <= 18446744073709551615:
            return True
        return False
    raise ValueError("argument must be int")
