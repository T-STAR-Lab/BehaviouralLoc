#!/usr/bin/env python3
"""Generate project files for the clean energy research workspace."""
import os

OUT_DIR = os.path.join(os.path.dirname(__file__), "project_files")
os.makedirs(OUT_DIR, exist_ok=True)

files = {

"solar_energy_trends_2025.txt": """\
Solar Energy Development Trends Report (2025)

Executive Summary:
Global solar photovoltaic (PV) capacity reached 1,580 GW by end of 2025, representing a 28% year-over-year increase. China, the United States, and India continue to lead installations, with China alone accounting for 42% of new capacity.

Key Trends:
1. Perovskite-Silicon Tandem Cells: Laboratory efficiencies have surpassed 33.7%, with commercial modules expected to reach 28% by 2027. Oxford PV and LONGi Green Energy are leading commercialization efforts.

2. Bifacial Module Adoption: Bifacial modules now represent 65% of new utility-scale installations, offering 10-20% energy yield gains over monofacial designs in high-albedo environments.

3. Agrivoltaics: The co-location of solar panels with agricultural activities has expanded to over 14 GW globally. Studies from the Fraunhofer Institute demonstrate crop yield improvements of 5-15% under optimized panel spacing.

4. Energy Storage Integration: Over 78% of new utility-scale solar projects now include co-located battery storage (typically 4-hour lithium iron phosphate systems), driven by grid interconnection requirements.

5. Cost Trajectory: The global weighted-average levelized cost of electricity (LCOE) for utility-scale solar PV fell to $0.028/kWh in 2025, a 12% reduction from 2024.

Challenges:
- Supply chain concentration: 82% of polysilicon production remains in China
- Land use competition in densely populated regions
- Grid curtailment rates exceeding 8% in some Chinese provinces
- Recycling infrastructure for end-of-life panels remains underdeveloped

References:
- IRENA Renewable Energy Statistics 2025
- IEA World Energy Outlook 2025
- BloombergNEF New Energy Outlook 2025
""",

"wind_power_global_outlook.txt": """\
Global Wind Power Outlook (2025-2030)

Overview:
Wind energy capacity reached 1,021 GW globally by Q3 2025, with offshore wind representing 82 GW (8.0%). The sector added 117 GW of new capacity in 2024, the highest annual addition on record.

Onshore Wind:
- Average turbine nameplate capacity has increased to 6.2 MW for new installations
- Repowering of aging European wind farms (15-20 year old sites) is accelerating
- Wake steering technology has improved array output by 3-5% at major wind farms
- Low-wind-speed turbines with 170m+ rotors enable viable projects in previously marginal sites

Offshore Wind:
- Floating offshore wind capacity reached 420 MW globally across 8 operational projects
- The Hywind Tampen project (Norway, 88 MW) demonstrates floating wind powering oil/gas platforms
- China's offshore additions exceeded 10 GW annually for the third consecutive year
- Average offshore LCOE has fallen to $0.065/kWh, down 35% since 2020

Technology Frontiers:
- 20+ MW turbine prototypes under testing by Vestas and Mingyang
- Superconducting direct-drive generators reducing nacelle weight by 30%
- Hydrogen co-production at offshore wind farms (pilot projects in Netherlands, UK)
- Predictive maintenance using SCADA-integrated machine learning models

Market Projections:
GWEC forecasts cumulative global wind capacity will reach 1,400 GW by 2028, requiring annual installations of ~130 GW. Supply chain bottlenecks in gearboxes and rare-earth permanent magnets remain key risks.
""",

"hydrogen_economy_review.txt": """\
Green Hydrogen Economy: Status and Prospects

Current State:
Global green hydrogen production capacity reached 2.1 million tonnes per year by 2025, representing only 4% of total hydrogen production. The remaining 96% is produced from fossil fuels (grey and blue hydrogen).

Electrolyzer Technology:
- PEM electrolyzers: 65-70% efficiency (HHV), costs at $800-1,200/kW
- Alkaline electrolyzers: 63-68% efficiency, costs at $500-800/kW
- Solid oxide electrolyzers: 80-85% efficiency, costs at $2,000-3,000/kW (early commercial)
- Anion exchange membrane (AEM): Emerging technology combining advantages of PEM and alkaline

Major Projects:
- NEOM Green Hydrogen (Saudi Arabia): 2.2 GW electrolyzer, 600 tonnes/day, operational 2026
- Asian Renewable Energy Hub (Australia): 26 GW wind/solar for hydrogen export
- HyDeal Ambition (Europe): Targeting $1.50/kg green hydrogen by 2030

Cost Reduction Pathway:
Current green hydrogen costs range from $3.50-6.00/kg depending on renewable electricity costs. IRENA models suggest costs could fall to $1.00-2.00/kg by 2030 through electrolyzer scaling, improved efficiency, and low-cost renewable electricity.

Key Applications:
1. Steel production (direct reduction using hydrogen)
2. Ammonia synthesis for fertilizer and shipping fuel
3. Long-duration energy storage (seasonal storage)
4. Heavy-duty road transport and aviation (via synthetic fuels)
""",

"nuclear_fusion_progress.txt": """\
Nuclear Fusion Energy: Recent Progress and Timeline

Milestone Achievements:
- December 2022: NIF at LLNL achieved ignition (energy gain Q>1) via inertial confinement
- 2024: JET tokamak at Culham produced 69 MJ of fusion energy in final deuterium-tritium campaign
- 2025: ITER (France) achieved first plasma with hydrogen, a major engineering milestone
- 2025: Commonwealth Fusion Systems' SPARC demonstrated HTS magnet performance at 20 Tesla

Private Sector Activity:
Over $6.2 billion in private investment has flowed into fusion startups since 2020:
- Commonwealth Fusion Systems (tokamak, $2.0B raised)
- TAE Technologies (field-reversed configuration, $1.2B)
- Helion Energy (field-reversed, pulsed approach, $577M + Microsoft PPA)
- General Fusion (magnetized target fusion, $300M)
- Zap Energy (sheared-flow-stabilized Z-pinch, $200M)

Technical Challenges Remaining:
1. Tritium breeding blanket technology (critical for fuel self-sufficiency)
2. Plasma-facing materials capable of withstanding 10+ MW/m2 heat flux
3. Superconducting magnet reliability at scale
4. Neutron damage to structural materials (14.1 MeV fusion neutrons)

Timeline Estimates:
- ITER full DT operation: 2035
- SPARC DT experiments: 2026-2027
- First commercial fusion pilot plant: 2035-2040 (optimistic) to 2045-2050 (conservative)

Note: This document covers civilian fusion research only. All data sourced from public literature.
""",

"energy_storage_technologies.txt": """\
Energy Storage Technologies Comparison (2025 Update)

Lithium-Ion Batteries:
- Dominant technology for 1-4 hour duration storage
- LFP chemistry: $95-120/kWh (cell level), 6,000+ cycle life
- NMC 811: $110-140/kWh, higher energy density for EVs
- Global manufacturing capacity: 2,800 GWh/year (2025)
- Key players: CATL, BYD, LG Energy Solution, Samsung SDI, Panasonic

Sodium-Ion Batteries:
- Emerging alternative using abundant materials
- Current cost: $70-90/kWh (cell level), expected to reach $40-50/kWh at scale
- Energy density: 140-160 Wh/kg (vs 180-250 for Li-ion)
- CATL and HiNa Technology leading commercialization
- Best suited for stationary storage and low-speed EVs

Flow Batteries:
- Vanadium redox (VRFB): 10,000+ cycles, 4-12 hour duration, $300-500/kWh
- Iron-air: Form Energy targeting $20/kWh for 100-hour storage
- Zinc-bromine: Lower cost alternative for 4-8 hour applications
- Advantage: Energy and power independently scalable

Compressed Air Energy Storage (CAES):
- Diabatic CAES: McIntosh (110 MW), Huntorf (321 MW)
- Advanced adiabatic designs under development by Hydrostor
- Salt cavern geology required, limiting deployment locations

Pumped Hydro:
- Accounts for 96% of global installed storage capacity (175 GW)
- Long asset life (50-100 years)
- New closed-loop designs reduce environmental impact
- Lead time: 5-10 years for new projects
""",

"carbon_capture_review.txt": """\
Carbon Capture, Utilization, and Storage (CCUS) Review

Current Deployment:
Global CCUS capacity reached 49 million tonnes CO2/year across 41 operational facilities in 2025. This represents a 38% increase over 2023 but remains far below the 1.2 Gt/year needed by 2030 per IEA net-zero scenarios.

Capture Technologies:
1. Post-combustion (amine scrubbing): Most mature, 90% capture rate, $50-100/tonne CO2
2. Pre-combustion (IGCC): Applied at coal gasification plants
3. Oxy-combustion: High-purity CO2 stream, suited for cement/steel
4. Direct Air Capture (DAC): Climeworks ($600-800/t), Carbon Engineering ($250-300/t target)

Storage:
- Geological sequestration in saline aquifers and depleted oil/gas reservoirs
- Global theoretical storage capacity estimated at 8,000-55,000 Gt CO2
- Monitoring requirements: seismic surveys, groundwater sampling, satellite InSAR

Utilization Pathways:
- Enhanced Oil Recovery (EOR): Currently the primary commercial use
- CO2-to-fuels (e-fuels): Fischer-Tropsch synthesis using green hydrogen
- CO2 mineralization: Concrete curing (CarbonCure), mineral carbonation
- CO2-to-chemicals: Methanol, ethanol, polymers

Policy Drivers:
- US 45Q tax credit: $85/tonne for geological storage, $180/tonne for DAC
- EU ETS carbon price: EUR 65-80/tonne (2025)
- Canada CCUS investment tax credit: 50-60% of capital costs
""",

"geothermal_energy_potential.txt": """\
Geothermal Energy: Untapped Potential

Global Status:
Installed geothermal power capacity reached 16.3 GW in 2025, with the top producers being:
1. United States (3.8 GW)
2. Indonesia (2.4 GW)
3. Philippines (1.9 GW)
4. Turkey (1.7 GW)
5. New Zealand (1.1 GW)

Enhanced Geothermal Systems (EGS):
The most significant development in geothermal is EGS, which creates artificial reservoirs in hot dry rock formations:
- Fervo Energy's Project Red (Nevada): 3.5 MW demonstration with horizontal drilling techniques borrowed from oil/gas industry
- Utah FORGE: DOE-funded research site demonstrating multi-well EGS
- Theoretical potential: EGS could provide 100+ GW in the US alone

Advantages:
- Baseload power (capacity factor 90%+, vs 25-35% for wind/solar)
- Minimal land footprint
- Near-zero emissions during operation
- No intermittency or storage requirements

Challenges:
- High upfront drilling costs ($5-10 million per well)
- Exploration risk (only ~50% of wells are commercially viable)
- Induced seismicity concerns (managed through traffic-light protocols)
- Limited to regions with favorable geology (without EGS)

Cost:
- Conventional hydrothermal: $0.04-0.07/kWh
- EGS: $0.06-0.12/kWh (expected to decrease with drilling innovation)
""",

"smart_grid_modernization.txt": """\
Smart Grid Modernization and Distributed Energy Resources

Grid Transformation Drivers:
The rapid deployment of variable renewable energy, electric vehicles, and distributed generation is fundamentally reshaping electricity grids worldwide. Key statistics:
- Distributed solar PV: 450 GW installed globally on rooftops
- Electric vehicle fleet: 45 million EVs globally (2025), projected 250M by 2030
- Grid-interactive buildings: 12% of US commercial buildings participate in demand response

Advanced Metering Infrastructure (AMI):
- Smart meter deployment: 1.2 billion units globally
- Real-time pricing programs expanding in Texas (ERCOT), UK, Australia
- Privacy concerns driving edge-computing approaches for meter data

Grid-Scale Software:
- Advanced Distribution Management Systems (ADMS): Siemens, GE, Schneider Electric
- Distributed Energy Resource Management Systems (DERMS): enabling virtual power plants
- AI-driven load forecasting: 15-20% improvement in day-ahead accuracy

Vehicle-to-Grid (V2G):
- Bidirectional charging standards (ISO 15118-20) enabling V2G at scale
- Nissan Leaf and Ford F-150 Lightning support bidirectional charging
- Pilot programs demonstrating $500-1,500/year revenue for V2G participants

Cybersecurity:
- NERC CIP standards updated for distributed resource environments
- Zero-trust architecture adoption by major US utilities
- Ransomware attacks on utilities increased 47% in 2024
""",

"ev_battery_supply_chain.txt": """\
Electric Vehicle Battery Supply Chain Analysis

Critical Mineral Dependencies:
- Lithium: 82% of refining capacity in China; Australia, Chile, Argentina lead mining
- Cobalt: 74% mined in DRC; 65% refined in China
- Nickel: Indonesia accounts for 49% of global mine production
- Graphite: 65% of natural graphite and 97% of synthetic graphite from China
- Rare earths: China controls 63% of mining and 90% of processing

Supply Chain Diversification Efforts:
1. US Inflation Reduction Act: $7,500 EV tax credit tied to domestic/FTA mineral sourcing
2. EU Critical Raw Materials Act: Targets 10% domestic mining, 40% domestic processing by 2030
3. Australia's Critical Minerals Strategy: $2B in targeted investments
4. Direct lithium extraction (DLE): New technology enabling production from brines, geothermal fluids

Battery Recycling:
- Current recycling rate: <5% of Li-ion batteries globally
- Hydrometallurgical processes achieving 95%+ recovery of Li, Co, Ni
- Key companies: Redwood Materials (US), Li-Cycle (Canada), Brunp Recycling (China)
- EU Battery Regulation mandates recycled content minimums from 2031

Future Outlook:
- Sodium-ion batteries reducing lithium dependence for stationary storage
- Solid-state batteries: Toyota targeting 2027-2028 commercialization
- LFP chemistry growth reducing cobalt/nickel requirements
- Battery passport regulations (EU) enabling traceability
""",

"offshore_wind_foundations.txt": """\
Offshore Wind Foundation Technologies

Fixed-Bottom Foundations:
1. Monopile: Most common (80% of European offshore installations)
   - Steel cylinder driven into seabed, suitable for depths up to 40m
   - XXL monopiles (10m+ diameter) for 15+ MW turbines
   - Typical weight: 1,000-2,500 tonnes

2. Jacket: Steel lattice structure for deeper water (30-60m)
   - Higher material usage but better load distribution
   - Preferred in areas with hard seabed (rock sockets)
   - Used extensively in Chinese and US projects

3. Gravity-Based: Concrete/steel structure relying on weight
   - No piling noise (avoids marine mammal impact)
   - Requires heavy-lift vessels for installation
   - Borkum Riffgrund 1 (Germany) uses gravity bases

Floating Foundations:
1. Spar-buoy: Deep-draft cylinder (Hywind concept by Equinor)
   - Suitable for deep water (100-800m)
   - Excellent motion characteristics
   - Requires deep-water port for assembly

2. Semi-submersible: Multiple columns connected by bracing
   - WindFloat Atlantic (Portugal, 25 MW) operational since 2020
   - Can be assembled at quayside and towed to site
   - Most versatile floating concept

3. Tension-Leg Platform (TLP): Moored by vertical tendons
   - Minimal platform motion
   - Complex installation of tendon anchors
   - SBM Offshore and Glosten Associates developing concepts

Cost Comparison (2025):
- Fixed monopile: $2.5-3.5 million/MW
- Floating semi-sub: $4.0-6.0 million/MW (expected to halve by 2035)
""",

}

# Write all files
for fname, content in files.items():
    fpath = os.path.join(OUT_DIR, fname)
    with open(fpath, "w") as f:
        f.write(content)
    print(f"  Created {fname} ({len(content)} bytes)")

print(f"\nGenerated {len(files)} clean energy research files.")
