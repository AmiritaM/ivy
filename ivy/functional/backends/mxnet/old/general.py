"""
Collection of MXNet general functions, wrapped to fit Ivy syntax and signature.
"""

# global
import ivy
_round = round
import logging
import mxnet as _mx
import numpy as _np
import math as _math
from numbers import Number
from operator import mul as _mul
from functools import reduce as _reduce
import multiprocessing as _multiprocessing

# local
from ivy.functional.ivy.old import default_dtype
from ivy.functional.ivy.device import default_device
from ivy.functional.backends.mxnet.device import _callable_dev
from ivy.functional.backends.mxnet.general import unstack
from ivy.functional.backends.mxnet import _handle_flat_arrays_in_out, _mxnet_init_context,\
    _scalar_or_flat_array_to_scalar, _handle_flat_arrays_in, _flat_array_to_1_dim_array, _1_dim_array_to_flat_array

#temporary imports
from ivy.functional.backends.mxnet.general import linspace


DTYPE_TO_STR = {_np.dtype('int8'): 'int8',
                _np.dtype('int16'): 'int16',
                _np.dtype('int32'): 'int32',
                _np.dtype('int64'): 'int64',
                _np.dtype('uint8'): 'uint8',
                _np.dtype('uint16'): 'uint16',
                _np.dtype('uint32'): 'uint32',
                _np.dtype('uint64'): 'uint64',
                'bfloat16': 'bfloat16',
                _np.dtype('float16'): 'float16',
                _np.dtype('float32'): 'float32',
                _np.dtype('float64'): 'float64',
                _np.dtype('bool'): 'bool',

                _np.int8: 'int8',
                _np.int16: 'int16',
                _np.int32: 'int32',
                _np.int64: 'int64',
                _np.uint8: 'uint8',
                _np.uint16: 'uint16',
                _np.uint32: 'uint32',
                _np.uint64: 'uint64',
                _np.float16: 'float16',
                _np.float32: 'float32',
                _np.float64: 'float64',
                _np.bool_: 'bool'}

DTYPE_FROM_STR = {'int8': _np.int8,
                'int16': _np.int16,
                'int32': _np.int32,
                'int64': _np.int64,
                'uint8': _np.uint8,
                'uint16': _np.uint16,
                'uint32': _np.uint32,
                'uint64': _np.uint64,
                'bfloat16': 'bfloat16',
                'float16': _np.float16,
                'float32': _np.float32,
                'float64': _np.float64,
                'bool': _np.bool_}


# API #
# ----#









def dtype_bits(dtype_in):
    dtype_str = dtype_to_str(dtype_in)
    if 'bool' in dtype_str:
        return 1
    return int(dtype_str.replace("<class 'numpy.", '').replace("'>", '').replace('uint', '').replace(
        'int', '').replace('bfloat', '').replace('float', ''))


equal = lambda x1, x2: x1 == x2
equal.__name__ = 'equal'

shape = lambda x, as_tensor=False: _mx.nd.shape_array(x) if as_tensor else x.shape
shape.__name__ = 'shape'
get_num_dims = lambda x, as_tensor=False:\
    _mx.nd.shape_array(_mx.nd.shape_array(x)).reshape([]) if as_tensor else len(x.shape)
minimum = lambda x, y: _mx.nd.array(_mx.nd.minimum(_scalar_or_flat_array_to_scalar(x), _scalar_or_flat_array_to_scalar(y)))
maximum = lambda x, y: _mx.nd.array(_mx.nd.maximum(_scalar_or_flat_array_to_scalar(x), _scalar_or_flat_array_to_scalar(y)))


@_handle_flat_arrays_in_out
def clip(x, x_min, x_max):
    return _mx.nd.clip(_mx.nd.array(x), x_min, x_max)


# noinspection PyShadowingBuiltins
@_handle_flat_arrays_in_out
def abs(x):
    return _mx.nd.abs(x)

argmin = lambda x, axis=0: _mx.nd.argmin(x, axis)


@_handle_flat_arrays_in_out
def cast(x, dtype):
    return x.astype(dtype)


astype = cast


# noinspection PyUnresolvedReferences
def arange(stop, start=0, step=1, dtype=None, dev=None):
    cont = _mxnet_init_context(default_device(dev))
    stop = stop if isinstance(stop, Number) else stop.asscalar()
    start = start if isinstance(start, Number) else start.asscalar()
    step = step if isinstance(step, Number) else step.asscalar()
    return _mx.nd.arange(start, stop, ctx=cont, step=step, dtype=dtype)




@_handle_flat_arrays_in_out
def concatenate(xs, axis=-1):
    return _mx.nd.concat(*xs, dim=axis)


def stack(xs, axis=0):
    if xs[0].shape == ():
        return _mx.nd.reshape(_mx.nd.stack(*[_flat_array_to_1_dim_array(x) for x in xs], axis=axis), -1)
    return _mx.nd.stack(*xs, axis=axis)








def transpose(x, axes=None):
    if axes is None:
        num_dims = len(x.shape)
        axes = list(range(num_dims))
        axes.reverse()
    return _mx.nd.transpose(x, axes)


@_handle_flat_arrays_in_out
def where(condition, x1, x2):
    x_shape = list(x1.shape)
    condition_shape = list(condition.shape)
    if x_shape == condition_shape:
        res = _mx.nd.where(condition, x1, x2)
        return res
    tile_reps = [int(x / c) for x, c in zip(x_shape, condition_shape)]
    tiled_condition = _mx.nd.tile(condition, tile_reps)
    return _mx.nd.where(tiled_condition, x1, x2)


def indices_where(x):
    x_shape = x.shape
    x_flat = x.reshape((1, -1,))
    flat_indices = x_flat.astype('int32').tostype('csr').indices
    if flat_indices.shape == (0,):
        res = flat_indices.reshape((0, len(x_shape)))
        return res
    res = _mx.nd.swapaxes(_mx.nd.unravel_index(flat_indices, x_shape), 0, 1)
    return res


reshape = lambda x, new_shape: x.reshape(new_shape)


def broadcast_to(x, new_shape):
    x_shape = list(x.shape)
    num_x_dims = len(x_shape)
    num_shape_dims = len(new_shape)
    diff = num_shape_dims - num_x_dims
    if diff == 0:
        return _mx.nd.broadcast_to(x, new_shape)
    x = _mx.nd.reshape(x, [1]*diff + x_shape)
    return _mx.nd.broadcast_to(x, new_shape)


def squeeze(x, axis=None):
    if x.shape == ():
        if axis is None or axis == 0 or axis == -1:
            return x
        raise Exception('tried to squeeze a zero-dimensional input by axis {}'.format(axis))
    res = _mx.nd.squeeze(x, axis)
    if axis is None:
        return _1_dim_array_to_flat_array(res)
    return res


# noinspection PyShadowingNames



def zeros_like(x, dtype=None, dev=None):
    if x.shape == ():
        return _mx.nd.array(0., ctx=_mxnet_init_context(default_device(dev)))
    mx_zeros = _mx.nd.zeros_like(x, ctx=_mxnet_init_context(default_device(dev)))
    return mx_zeros if not dtype else mx_zeros.astype(dtype)


def full(shape, fill_value, dtype=None, device=None):
    shape = ivy.shape_to_tuple(shape)
    cont = _mxnet_init_context(default_device(device))
    if len(shape) == 0 or 0 in shape:
        return _1_dim_array_to_flat_array(
            _mx.nd.full((1,), fill_value, cont, dtype_from_str(default_dtype(dtype, fill_value))))
    return _mx.nd.full(shape, fill_value, cont, dtype_from_str(default_dtype(dtype, fill_value)))

# noinspection PyUnusedLocal
one_hot = lambda indices, depth, dev=None: _mx.nd.one_hot(indices, depth)


def cross(x1, x2):
    a1 = x1[..., 0:1]
    a2 = x1[..., 1:2]
    a3 = x1[..., 2:3]
    b1 = x2[..., 0:1]
    b2 = x2[..., 1:2]
    b3 = x2[..., 2:3]
    res1 = a2*b3 - a3*b2
    res2 = a3*b1 - a1*b3
    res3 = a1*b2 - a2*b1
    res = _mx.nd.concat(res1, res2, res3, dim=-1)
    return res


def matmul(x1, x2):
    expanded = False
    x1_shape = list(x1.shape)
    x2_shape = list(x2.shape)
    if len(x1_shape) != 3:
        num_x1_dims = len(x1_shape)
        x1 = _mx.nd.reshape(x1, [1]*max(2-num_x1_dims, 0) + [-1] + x1_shape[-min(num_x1_dims, 2):])
        expanded = True
    if len(x2_shape) != 3:
        num_x2_dims = len(x2_shape)
        x2 = _mx.nd.reshape(x2, [1]*max(2-num_x2_dims, 0) + [-1] + x2_shape[-min(num_x2_dims, 2):])
        expanded = True
    x1_batch_size = x1.shape[0]
    x2_batch_size = x2.shape[0]
    if x1_batch_size > x2_batch_size:
        x2 = _mx.nd.tile(x2, (int(x1_batch_size/x2_batch_size), 1, 1))
    elif x2_batch_size > x1_batch_size:
        x1 = _mx.nd.tile(x1, (int(x2_batch_size / x1_batch_size), 1, 1))
    res = _mx.nd.batch_dot(x1, x2)
    if expanded:
        return _mx.nd.reshape(res, list(x1_shape[:-1]) + [res.shape[-1]])
    return res


cumsum = lambda x, axis=0: _mx.nd.cumsum(x, axis if axis >= 0 else axis % len(x.shape))


def cumprod(x, axis=0, exclusive=False):
    array_stack = [_mx.nd.expand_dims(chunk, axis) for chunk in unstack(x, axis)]
    if exclusive:
        array_stack = [_mx.nd.ones_like(array_stack[0])] + array_stack[:-1]
    new_array_list = [array_stack[0]]
    for array_chunk in array_stack[1:]:
        new_array_list.append(new_array_list[-1] * array_chunk)
    return _mx.nd.concat(*new_array_list, dim=axis)


def identity(n, dtype='float32', batch_shape=None, dev=None):
    mat = _mx.nd.eye(n, dtype=dtype).copyto(_mxnet_init_context(default_device(dev)))
    if batch_shape is None:
        return mat
    else:
        reshape_dims = [1]*len(batch_shape) + [n, n]
        tile_dims = list(batch_shape) + [1, 1]
        res = _mx.nd.tile(_mx.nd.reshape(mat, reshape_dims), tile_dims)
        return res


def meshgrid(*xs, indexing='ij'):
    # ToDo: implement this without reliance on NumPy backend
    xs_np = [x.as_np_ndarray() for x in xs]
    return tuple([item.as_nd_ndarray() for item in _mx.np.meshgrid(*xs_np, indexing=indexing)])


# noinspection PyShadowingNames
def scatter_flat(indices, updates, size=None, tensor=None, reduction='sum', dev=None):
    if ivy.exists(tensor):
        raise Exception('MXNet scatter_flat does not support scattering into an pre-existing tensor.')
    if reduction == 'replace':
        return _mx.nd.scatter_nd(updates, _mx.nd.expand_dims(indices, 0), [size]).copyto(_mxnet_init_context(default_device(dev)))
    else:
        raise Exception('MXNet scatter_flat currently only supports reduction mode "replace", but {} selected.'.
                        format(reduction))


# noinspection PyShadowingNames
def scatter_nd(indices, updates, shape=None, tensor=None, reduction='sum', dev=None):
    if ivy.exists(tensor):
        raise Exception('MXNet scatter_flat does not support scattering into an pre-existing tensor.')
    if dev is None:
        dev = _callable_dev(indices)
    shape = list(shape)
    num_idx_dims = len(indices.shape)
    transpose_order = [num_idx_dims-1] + list(range(num_idx_dims-1))
    indices = _mx.nd.transpose(indices, transpose_order)
    shape = shape if type(shape) is list else shape.asnumpy().astype(_np.int32).tolist()
    if reduction == 'replace':
        return _mx.nd.scatter_nd(updates, indices, shape).copyto(_mxnet_init_context(dev))
    else:
        raise Exception('MXNet scatter_nd currently only supports reduction mode "replace", but {} selected.'.
                        format(reduction))


def gather(params, indices, axis=-1, dev=None):
    if dev is None:
        dev = _callable_dev(params)
    index_slices = unstack(indices, -1)
    res = _mx.nd.concat(
        *[_mx.nd.expand_dims(_mx.nd.pick(params, idx_slice, axis), -1) for idx_slice in index_slices], dim=-1)
    res = _mx.nd.reshape(res, indices.shape)
    return res.copyto(_mxnet_init_context(dev))


def gather_nd(params, indices, dev=None):
    if dev is None:
        dev = _callable_dev(params)
    indices_shape = indices.shape
    num_idx_dims = len(indices_shape)
    transpose_order = [num_idx_dims-1] + list(range(num_idx_dims-1))
    indices = _mx.nd.transpose(indices, transpose_order)
    return _mx.nd.gather_nd(params, indices).copyto(_mxnet_init_context(dev))


def linear_resample(x, num_samples, axis=-1):
    x_shape = list(x.shape)
    num_x_dims = len(x_shape)
    axis = axis % num_x_dims
    x_pre_shape = x_shape[0:axis]
    x_pre_size = _reduce(_mul, x_pre_shape) if x_pre_shape else 1
    num_pre_dims = len(x_pre_shape)
    num_vals = x.shape[axis]
    x_post_shape = x_shape[axis+1:]
    x_post_size = _reduce(_mul, x_post_shape) if x_post_shape else 1
    num_post_dims = len(x_post_shape)
    xp = _mx.nd.reshape(_mx.nd.arange(num_vals*x_pre_size*x_post_size), x_shape)
    x_coords = _mx.nd.arange(num_samples) * ((num_vals-1)/(num_samples-1)) * x_post_size
    x_coords = _mx.nd.reshape(x_coords, [1]*num_pre_dims + [num_samples] + [1]*num_post_dims)
    x_coords = _mx.nd.broadcast_to(x_coords, x_pre_shape + [num_samples] + x_post_shape)
    slc = [slice(None)] * num_x_dims
    slc[axis] = slice(0, 1, 1)
    x_coords = x_coords + xp[tuple(slc)]
    x = _mx.nd.reshape(x, (-1,))
    xp = _mx.nd.reshape(xp, (-1,))
    x_coords = _mx.nd.reshape(x_coords, (-1,))
    ret = _mx.nd.array(_mx.np.interp(x_coords.asnumpy(), xp.asnumpy(), x.asnumpy()))
    return _mx.nd.reshape(ret, x_pre_shape + [num_samples] + x_post_shape)


def dtype(x, as_str=False):
    dt = x.dtype
    if as_str:
        return dtype_to_str(dt)
    return x.dtype


def dtype_to_str(dtype_in):
    if isinstance(dtype_in, str):
        return dtype_in
    return DTYPE_TO_STR[dtype_in]


def dtype_from_str(dtype_in):
    if not isinstance(dtype_in, str):
        return dtype_in
    return DTYPE_FROM_STR[dtype_in]


# noinspection PyUnusedLocal
def compile(func, dynamic=True, example_inputs=None, static_argnums=None, static_argnames=None):
    logging.warning('MXnet does not support compiling arbitrary functions, '
                    'consider writing a function using MXNet Symbolic backend instead for compiling.\n'
                    'Now returning the unmodified function.')
    return func


current_framework_str = lambda: 'mxnet'
current_framework_str.__name__ = 'current_framework_str'
multiprocessing = lambda context=None: _multiprocessing if context is None else _multiprocessing.get_context(context)






