# Copyright 2022 SenseTime Group Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import numpy as np


def merge_batchnorm_nodes(model):
    """
    Version specific for 0.3.0 and 0.3.1 and 1.0.x
    A sequence of constant-constant-add nodes with consistent blob flow
    corresponds to one holistic BatchNorm layer in caffe.
    This method merges the nodes into one node corresponding
    to that layer.
    """
    nodes = model.graph.node[:]
    del model.graph.node[:]

    idx = 0
    while idx < len(nodes):
        node = nodes[idx]
        if node.op_type != "Constant" or idx + 2 >= len(nodes):
            model.graph.node.extend([node])
            idx += 1
            continue

        constant_node_weight = node
        node = nodes[idx + 1]
        if node.op_type != "Constant":
            model.graph.node.extend([constant_node_weight])
            idx += 1
            continue

        constant_node_bias = node
        node = nodes[idx + 2]
        if (
            node.op_type != "BatchNormalization"
            or constant_node_weight.output[0] != node.input[1]
            or constant_node_bias.output[0] != node.input[2]
        ):
            model.graph.node.extend([constant_node_weight])
            idx += 1
            continue

        weight_attributes = dict(
            zip(
                [attr.name for attr in constant_node_weight.attribute],
                constant_node_weight.attribute,
            )
        )
        weight = np.frombuffer(weight_attributes["value"].t.raw_data, dtype=np.float32)
        assert np.all(weight == 1)
        bias_attributes = dict(
            zip(
                [attr.name for attr in constant_node_bias.attribute],
                constant_node_bias.attribute,
            )
        )
        bias = np.frombuffer(bias_attributes["value"].t.raw_data, dtype=np.float32)
        assert np.all(bias == 0)
        batchnorm_node = node
        batchnorm_node.input[1] = ""
        batchnorm_node.input[2] = ""
        model.graph.node.extend([batchnorm_node])
        idx += 3