# -*- coding: utf-8 -*-
"""
Created on Sat Nov 17 09:48:34 2018

@author: yoelr
"""
from biosteam.stream import Stream, mol_flow_dim, mass_flow_dim, vol_flow_dim
from biosteam import Q_, pd, np
from biosteam.exceptions import DimensionError
import copy

DataFrame = pd.DataFrame
ExcelWriter = pd.ExcelWriter

__all__ = ('stream_table', 'save_reports', 'report_cost',
           'report_results', 'report_heat_utilities', 'report_power_utilities')

# %% Helpful functions

def _units_wt_cost(units):
    """Remove units that do not have capital or operating cost."""
    r = 0
    units = list(units)
    for i in range(len(units)):
        i -= r
        unit = units[i]
        Summary = unit.results['Summary']
        ci = Summary['Purchase cost']
        co = Summary['Utility cost']
        if not (ci or co):
            del units[i]
            r += 1
    return units

def _units_sort_by_cost(units):
    """Sort by first grouping units by type and then order groups by maximum capital."""
    unit_types = list({type(u).__name__ for u in units})
    type_dict = {ut:[] for ut in unit_types}
    for u in units:
        ut = type(u).__name__
        type_dict[ut].append(u)
    units = []
    unit_types.sort(key=lambda ut: max(u.results['Summary']['Purchase cost'] for u in type_dict[ut]), reverse=True)
    for key in unit_types:
        ulist = type_dict[key]
        ulist.sort(key=lambda x: x.results['Summary']['Purchase cost'], reverse=True)
        units += ulist
    return units

def save_reports(reports, file='Report.xlsx'):
    """Save a list of reports as an excel file.
    
    **Parameters**
    
        **reports:** iterable[DataFrame]
        
    """
    writer = ExcelWriter(file)
    n_row = 1
    for r in reports:
        label = r.columns.name
        r.to_excel(writer, startrow=n_row, index_label=label)
        n_row += len(r.index) + 2
    

# %% Units

def report_results(units):
    """Return a list of results reports for each unit type.

    **Parameters**

        **units:** iterable[Unit]
        
    **Returns:**
    
        **reports:** list[DataFrame]
    
    """
    units = _units_wt_cost(units)
    units.sort(key=(lambda u: type(u).__name__))
    
    # First report and set keys to compare with
    r = units[0].results
    keys = tuple(r.nested_keys())
    report = r.table()
    del units[0]
    
    # Make a list of reports, keeping all results with same keys in one report
    reports = []
    for u in units:
        r = u.results
        new_keys = tuple(r.nested_keys())
        if new_keys == keys:
            report = pd.concat((report, r.table(with_units=False)), axis=1)
        else:
            reports.append(report)
            report = r.table()
            keys = new_keys
    
    # Add the last report
    reports.append(report)
    
    return reports
    
def report_cost(units):
    """Return a cost report as a pandas DataFrame object.

    **Parameters**:

        **units:** array_like[Unit]
         
    **Returns**
    
        **unit_table:** [DataFrame] Units as indexes with the following columns
            * 'Unit Type': Type of unit
            * 'CI (10^6 USD)': Capital investment
            * 'OC (10^6 USD/yr)': Annual operating cost

    """
    columns = ('Type',
              f'CI (10^6 USD)',
              f'OC (10^6 USD/yr)')
    units = _units_wt_cost(units)
    units = _units_sort_by_cost(units)
    
    # Initialize data
    N_units = len(units)
    array = np.empty((N_units, 3), dtype=object)
    IDs = []
    types = array[0:, 0]
    C_cap = array[0:, 1]
    C_op = array[0:, 2]
    
    # Get data
    for i in range(N_units):
        unit = units[i]
        Summary = unit.results['Summary']
        types[i] = type(unit).__name__
        C_cap[i] = Summary['Purchase cost'] * unit.lang_factor / 1e6
        C_op[i] = Summary['Utility cost'] * unit.operating_days * 24  / 1e6
        IDs.append(unit.ID)
    
    return DataFrame(array, columns=columns, index=IDs)    

def report_heat_utilities(units):
    """Return a list of utility reports for each heat utility source.
    
    **Parameters**
    
        **units:** iterable[units]
        
    **Returns**
    
        **reports:** list[DataFrame]
        
    """
    # Sort heat utilities by unit type, then by utility Type
    units = sorted(units, key=(lambda u: type(u).__name__))
    heat_utils = []
    for u in units:
        heat_utils.extend(u.heat_utilities)
    try:
        heat_utils.sort(key=lambda hu: hu.results['ID'])
    except KeyError:
        for hu in heat_utils:
            if not hasattr(hu.results, 'ID'):
                raise ValueError(f'HeatUtility from {hu.results.source} is empty.')
    
    # First report and set Type to compare with
    hu = heat_utils[0]
    r = hu.results
    Type = r['ID']
    r = copy.copy(r)
    del r['ID']
    report = r.table()
    del heat_utils[0]
    
    # Make a list of reports, keeping all results with same Type in one report
    reports = []
    for hu in heat_utils:
        r = hu.results
        Type_new = r['ID']
        r = copy.copy(r)
        del r['ID']
        if Type == Type_new:
            report = pd.concat((report, r.table(with_units=False)), axis=1)
        else:
            report.columns.name = Type
            reports.append(report)
            report = r.table(with_units=True)
            Type = Type_new
    
    # Add the last report
    report.columns.name = Type
    reports.append(report)
    return reports
    

def report_power_utilities(units, **units_of_measure):
    # Sort power utilities by unit type
    units = sorted(units, key=(lambda u: type(u).__name__))
    power_utils = tuple(u.power_utility for u in units if u.power_utility)
    pu = power_utils[0]
    report = pu.results.table()
    for pu in power_utils:
        report = pd.concat((report, pu.results.table(with_units=False)), axis=1)
    return report

# %% Streams

def stream_table(streams, Flow='kmol/hr', **props) -> 'DataFrame':
    """Return a stream table as a pandas DataFrame object.

    **Parameters**:

         **streams:** array_like[Stream]
        
         **Flow:** [str] Units for flow rate

         **props:** [str] Additional stream properties and units as key-value pairs
    
    """
    # Get correct flow attributes
    flow_dim = Q_(0, Flow).dimensionality
    if flow_dim == mol_flow_dim:
        flow_attr = 'mol'
    elif flow_dim == mass_flow_dim:
        flow_attr = 'mass'
    elif flow_dim == vol_flow_dim:
        flow_attr = 'vol'
    else:
        raise DimensionError(f"Dimensions for flow units must be in molar, mass or volumetric flow rates, not '{flow_dim}'.")
    
    # Prepare rows and columns
    ss = streams
    species = type(ss[0])._specie_IDs
    n = len(ss)
    m = len(species)
    p = len(props)
    array = np.empty((m+p+5, n), dtype=object)
    IDs = n*[None]
    sources = array[0, :]
    sinks = array[1, :]
    phases = array[2, :]
    prop_molar_data = array[3:3+p+1,:]
    flows = array[p+3, :]
    array[p+4, :] = ''
    fracs = array[p+5:m+p+5, :]
    for j in range(n):
        s = ss[j]
        sources[j] = s.source[0]
        sinks[j] = s.sink[0]
        IDs[j] = s.ID
        phase = ''
        for i in s.phase:
            if i == 'l':
                phase += 'liquid|'
            elif i == 'L':
                phase += 'LIQUID|'
            elif i == 'g':
                phase += 'gas|'
            elif i == 's':
                phase += 'solid|'
        phase = phase.rstrip('|')
        phases[j] = phase
        flow_j = getattr(s, flow_attr)
        flows[j] = net_j = sum(flow_j)
        fracs[:,j] = flow_j/net_j if net_j > 0 else 0
        i = 0
        for attr, unit in props.items():
            prop_molar_data[i, j] = getattr(s, attr)
            i += 1
    
    # Set the right units
    units = Stream.units
    flows = Q_(flows, units[flow_attr]); flows.ito(Flow); flows = flows.magnitude
    i = 0
    prop_molar_keys = p*[None]
    for attr, unit in props.items():
        p = prop_molar_data[i]
        p = Q_(p, units[attr]); p.ito(unit); p = p.magnitude
        prop_molar_keys[i] = f'{attr} ({unit})'
        i += 1
    
    # Add spaces for readability
    species = list(species).copy()
    for i in range(m):
        species[i] = '- ' + species[i]
    
    # Make data frame object
    index = ('Source', 'Sink', 'Phase')  + tuple(prop_molar_keys) + (f'Flow ({Flow})', 'Composition:') + tuple(species)
    return DataFrame(array, columns=IDs, index=index)