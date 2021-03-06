# -*- coding: utf-8 -*-

# Copyright 2018, IBM.
#
# This source code is licensed under the Apache License, Version 2.0 found in
# the LICENSE.txt file in the root directory of this source tree.

"""Tests for bit reordering fix."""

import unittest

from qiskit import BasicAer, ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.exceptions import QiskitError
from qiskit.providers.ibmq import IBMQ, least_busy
from qiskit.test import QiskitTestCase, requires_qe_access, slow_test
from qiskit.tools.compiler import compile


class TestBitReordering(QiskitTestCase):
    """Test Qiskit's fix for the ibmq hardware reordering bug.

    The bug will be fixed with the introduction of qobj,
    in which case these tests can be used to verify correctness.
    """
    @slow_test
    @requires_qe_access
    def test_basic_reordering(self, qe_token, qe_url):
        """a simple reordering within a 2-qubit register"""
        sim, real = self._get_backends(qe_token, qe_url)
        if not sim or not real:
            raise unittest.SkipTest('no remote device available')

        qr = QuantumRegister(2)
        cr = ClassicalRegister(2)
        circuit = QuantumCircuit(qr, cr)
        circuit.h(qr[0])
        circuit.measure(qr[0], cr[1])
        circuit.measure(qr[1], cr[0])

        shots = 2000
        qobj_real = compile(circuit, real)
        qobj_sim = compile(circuit, sim)
        result_real = real.run(qobj_real).result(timeout=600)
        result_sim = sim.run(qobj_sim).result(timeout=600)
        counts_real = result_real.get_counts()
        counts_sim = result_sim.get_counts()
        self.log.info(counts_real)
        self.log.info(counts_sim)
        threshold = 0.1 * shots
        self.assertDictAlmostEqual(counts_real, counts_sim, threshold)

    @slow_test
    @requires_qe_access
    def test_multi_register_reordering(self, qe_token, qe_url):
        """a more complicated reordering across 3 registers of different sizes"""
        sim, real = self._get_backends(qe_token, qe_url)
        if not sim or not real:
            raise unittest.SkipTest('no remote device available')

        qr0 = QuantumRegister(2)
        qr1 = QuantumRegister(2)
        qr2 = QuantumRegister(1)
        cr0 = ClassicalRegister(2)
        cr1 = ClassicalRegister(2)
        cr2 = ClassicalRegister(1)
        circuit = QuantumCircuit(qr0, qr1, qr2, cr0, cr1, cr2)
        circuit.h(qr0[0])
        circuit.cx(qr0[0], qr2[0])
        circuit.x(qr1[1])
        circuit.h(qr2[0])
        circuit.cx(qr2[0], qr1[0])
        circuit.barrier()
        circuit.measure(qr0[0], cr2[0])
        circuit.measure(qr0[1], cr0[1])
        circuit.measure(qr1[0], cr0[0])
        circuit.measure(qr1[1], cr1[0])
        circuit.measure(qr2[0], cr1[1])

        shots = 4000
        qobj_real = compile(circuit, real)
        qobj_sim = compile(circuit, sim)
        result_real = real.run(qobj_real).result(timeout=600)
        result_sim = sim.run(qobj_sim).result(timeout=600)
        counts_real = result_real.get_counts()
        counts_sim = result_sim.get_counts()
        threshold = 0.2 * shots
        self.assertDictAlmostEqual(counts_real, counts_sim, threshold)

    def _get_backends(self, qe_token, qe_url):
        sim_backend = BasicAer.get_backend('qasm_simulator')
        try:
            IBMQ.enable_account(qe_token, qe_url)
            real_backends = IBMQ.backends(simulator=False)
            real_backend = least_busy(real_backends)
        except QiskitError:
            real_backend = None

        return sim_backend, real_backend
