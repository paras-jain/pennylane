# Copyright 2018-2019 Xanadu Quantum Technologies Inc.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
r"""
Contains the ``Interferometer`` template.
"""
#pylint: disable-msg=too-many-branches,too-many-arguments,protected-access
from pennylane.templates.decorator import template
from pennylane.ops import Beamsplitter, Rotation
from pennylane.templates.utils import (_check_shapes,
                                       _check_no_variable,
                                       _check_wires,
                                       _check_is_in_options)


@template
def Interferometer(theta, phi, varphi, wires, mesh='rectangular', beamsplitter='pennylane'):
    r"""General linear interferometer, an array of beamsplitters and phase shifters.

    For :math:`M` wires, the general interferometer is specified by
    providing :math:`M(M-1)/2` transmittivity angles :math:`\theta` and the same number of
    phase angles :math:`\phi`, as well as :math:`M-1` additional rotation
    parameters :math:`\varphi`.

    By specifying the keyword argument ``mesh``, the scheme used to implement the interferometer
    may be adjusted:

    * ``mesh='rectangular'`` (default): uses the scheme described in
      `Clements et al. <https://dx.doi.org/10.1364/OPTICA.3.001460>`__, resulting in a *rectangular* array of
      :math:`M(M-1)/2` beamsplitters arranged in :math:`M` slices and ordered from left
      to right and top to bottom in each slice. The first beamsplitter acts on
      wires :math:`0` and :math:`1`:

      .. figure:: ../../_static/clements.png
          :align: center
          :width: 30%
          :target: javascript:void(0);


    * ``mesh='triangular'``: uses the scheme described in `Reck et al. <https://dx.doi.org/10.1103/PhysRevLett.73.58>`__,
      resulting in a *triangular* array of :math:`M(M-1)/2` beamsplitters arranged in
      :math:`2M-3` slices and ordered from left to right and top to bottom. The
      first and fourth beamsplitters act on wires :math:`M-1` and :math:`M`, the second
      on :math:`M-2` and :math:`M-1`, and the third on :math:`M-3` and :math:`M-2`, and
      so on.

      .. figure:: ../../_static/reck.png
          :align: center
          :width: 30%
          :target: javascript:void(0);

    In both schemes, the network of :class:`~pennylane.ops.Beamsplitter` operations is followed by
    :math:`M` local :class:`~pennylane.ops.Rotation` Operations.

    The rectangular decomposition is generally advantageous, as it has a lower
    circuit depth (:math:`M` vs :math:`2M-3`) and optical depth than the triangular
    decomposition, resulting in reduced optical loss.

    This is an example of a 4-mode interferometer with beamsplitters :math:`B` and rotations :math:`R`,
    using ``mesh='rectangular'``:

    .. figure:: ../../_static/layer_interferometer.png
        :align: center
        :width: 60%
        :target: javascript:void(0);

    .. note::

        The decomposition as formulated in `Clements et al. <https://dx.doi.org/10.1364/OPTICA.3.001460>`__ uses a different
        convention for a beamsplitter :math:`T(\theta, \phi)` than PennyLane, namely:

        .. math:: T(\theta, \phi) = BS(\theta, 0) R(\phi)

        For the universality of the decomposition, the used convention is irrelevant, but
        for a given set of angles the resulting interferometers will be different.

        If an interferometer consistent with the convention from `Clements et al. <https://dx.doi.org/10.1364/OPTICA.3.001460>`__
        is needed, the optional keyword argument ``beamsplitter='clements'`` can be specified. This
        will result in each :class:`~pennylane.ops.Beamsplitter` being preceded by a :class:`~pennylane.ops.Rotation` and
        thus increase the number of elementary operations in the circuit.

    Args:
        theta (array): length :math:`M(M-1)/2` array of transmittivity angles :math:`\theta`
        phi (array): length :math:`M(M-1)/2` array of phase angles :math:`\phi`
        varphi (array): length :math:`M` array of rotation angles :math:`\varphi`
        wires (Sequence[int]): wires the interferometer should act on
        mesh (string): the type of mesh to use
        beamsplitter (str): if ``clements``, the beamsplitter convention from
          Clements et al. 2016 (https://dx.doi.org/10.1364/OPTICA.3.001460) is used; if ``pennylane``, the
          beamsplitter is implemented via PennyLane's ``Beamsplitter`` operation.

    Raises:
        ValueError: if inputs do not have the correct format
    """

    #############
    # Input checks
    _check_no_variable(beamsplitter, msg="'beamsplitter' cannot be differentiable")
    _check_no_variable(mesh, msg="'mesh' cannot be differentiable")

    wires = _check_wires(wires)

    weights_list = [theta, phi, varphi]
    n_wires = len(wires)
    n_if = n_wires*(n_wires-1)//2
    expected_shapes = [(n_if,), (n_if,), (n_wires,)]
    _check_shapes(weights_list, expected_shapes, msg="wrong shape of weight input(s) detected")

    _check_is_in_options(beamsplitter, ['clements', 'pennylane'], msg="did not recognize option {} for 'beamsplitter'"
                                                                      "".format(beamsplitter))
    _check_is_in_options(mesh, ['triangular', 'rectangular'], msg="did not recognize option {} for 'mesh'"
                                                                  "".format(mesh))
    ###############

    M = len(wires)

    if M == 1:
        # the interferometer is a single rotation
        Rotation(varphi[0], wires=wires[0])
        return

    n = 0  # keep track of free parameters

    if mesh == 'rectangular':
        # Apply the Clements beamsplitter array
        # The array depth is N
        for l in range(M):
            for k, (w1, w2) in enumerate(zip(wires[:-1], wires[1:])):
                #skip even or odd pairs depending on layer
                if (l+k)%2 != 1:
                    if beamsplitter == 'clements':
                        Rotation(phi[n], wires=[w1])
                        Beamsplitter(theta[n], 0, wires=[w1, w2])
                    else:
                        Beamsplitter(theta[n], phi[n], wires=[w1, w2])
                    n += 1

    elif mesh == 'triangular':
        # apply the Reck beamsplitter array
        # The array depth is 2*N-3
        for l in range(2*M-3):
            for k in range(abs(l+1-(M-1)), M-1, 2):
                if beamsplitter == 'clements':
                    Rotation(phi[n], wires=[wires[k]])
                    Beamsplitter(theta[n], 0, wires=[wires[k], wires[k+1]])
                else:
                    Beamsplitter(theta[n], phi[n], wires=[wires[k], wires[k+1]])
                n += 1

    # apply the final local phase shifts to all modes
    for i, p in enumerate(varphi):
        Rotation(p, wires=[wires[i]])