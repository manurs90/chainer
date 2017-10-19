import numpy

from chainer import cuda
from chainer import function_node
import chainer.functions
from chainer import utils
from chainer.utils import type_check


class Minimum(function_node.FunctionNode):
    """Element-wise minimum of input variables."""

    def check_type_forward(self, in_types):
        type_check.expect(
            in_types.size() == 2,
            in_types[0].dtype.kind == 'f',
            in_types[0].dtype == in_types[1].dtype,
            in_types[0].shape == in_types[1].shape
        )

    def forward_cpu(self, inputs):
        self.retain_inputs((0, 1))
        x1, x2 = inputs
        y = numpy.minimum(x1, x2)
        return utils.force_array(y),

    def forward_gpu(self, inputs):
        self.retain_inputs((0, 1))
        x1, x2 = inputs
        return cuda.cupy.minimum(x1, x2),

    def backward(self, indexes, grad_outputs):
        x1, x2 = self.get_retained_inputs()
        return MinimumGrad().apply((x1, x2, grad_outputs[0]))


class MinimumGrad(function_node.FunctionNode):

    def forward_cpu(self, inputs):
        self.retain_inputs((0, 1))
        x1, x2, gy = inputs
        gx1 = gy * (x1 <= x2)
        gx2 = gy * (x1 > x2)
        return utils.force_array(gx1), utils.force_array(gx2)

    def forward_gpu(self, inputs):
        self.retain_inputs((0, 1))
        x1, x2, gy = inputs
        gx1 = cuda.elementwise(
            'T x1, T x2, T gy', 'T gx1',
            'gx1 = (x1 <= x2) ? gy : (T)0.0',
            'minimum_bwd1')(x1, x2, gy)
        gx2 = cuda.elementwise(
            'T x1, T x2, T gy', 'T gx1',
            'gx1 = (x1 > x2) ? gy : (T)0.0',
            'minimum_bwd2')(x1, x2, gy)
        return gx1, gx2

    def backward(self, indexes, grad_outputs):
        x1, x2 = self.get_retained_inputs()
        ggx = grad_outputs[0] * 0 + grad_outputs[1] * 0
        cond = utils.force_array(x1.data <= x2.data)
        gggy = chainer.functions.where(cond, grad_outputs[0], grad_outputs[1])
        return ggx, ggx, gggy


def minimum(x1, x2):
    """Element-wise minimum of input variables.

    Args:
        x1 (~chainer.Variable): Input variables to be compared.
        x2 (~chainer.Variable): Input variables to be compared.

    Returns:
        ~chainer.Variable: Output variable.
    """
    return Minimum().apply((x1, x2))[0]
