# -*- coding: utf-8 -*-
"""
Created on Thu Jun 25 00:16:24 2020

@author: yrc2
"""
from biosteam import units
import biosteam as bst
from biosteam.process_tools import UnitGroup
from thermosteam import functional as fn
from biosteam import main_flowsheet as F
import thermosteam as tmo
import numpy as np

__all__ = ('test_example_sugarcane_subsystem',
)

def test_example_sugarcane_subsystem():
    """
    Test BioSTEAM by creating a conventional sugarcane fermentation and ethanol
    separation process.
    
    Examples
    --------
    >>> # Simply run this test and make sure not errors are raised
    >>> test_example_sugarcane_subsystem()

    """
    from biosteam.examples import ethanol_subsystem_example
    ethanol_sys = ethanol_subsystem_example()
    biorefinery = UnitGroup('Biorefinery', ethanol_sys.units)
    assert np.allclose(biorefinery.get_installed_cost(), 13.57808163192647)
    assert np.allclose(biorefinery.get_heating_duty(), 156.8807334325833)
    assert np.allclose(biorefinery.get_cooling_duty(), 104.4639430479312)
    assert np.allclose(biorefinery.get_electricity_consumption(), 0.40116044433570186)
    assert np.allclose(biorefinery.get_electricity_production(), 0.)
    