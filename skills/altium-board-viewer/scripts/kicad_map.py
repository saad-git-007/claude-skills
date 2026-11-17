"""Map board footprints to KiCad official 3D models (kicad-packages3D) and footprints (kicad-footprints).

RULES below are worked examples from one board; add your own in board.json "kicad_rules"
(same shape, tried first). Check each target name exists before relying on it: fetch_models.py
reports 404s. Browse https://gitlab.com/kicad/libraries/kicad-packages3D for exact names.
"""
import re
try:
    import cfg
    _EXTRA = [tuple(r) for r in cfg.KICAD_RULES]
except SystemExit:
    _EXTRA = []

# (match on designator-prefix, match on footprint regex) -> KiCad "Library:Name"
RULES = [
    ("C", r"(?i)1005", "Capacitor_SMD:C_0402_1005Metric"),
    ("C", r"(?i)1608", "Capacitor_SMD:C_0603_1608Metric"),
    ("C", r"(?i)2012", "Capacitor_SMD:C_0805_2012Metric"),
    ("C", r"(?i)3216", "Capacitor_SMD:C_1206_3216Metric"),
    ("C", r"(?i)RADIAL_6\.3", "Capacitor_THT:CP_Radial_D6.3mm_P2.50mm"),
    ("C", r"(?i)RADIAL_8\.0", "Capacitor_THT:CP_Radial_D8.0mm_P3.50mm"),
    ("C", r"(?i)RADIAL_5\.0", "Capacitor_THT:CP_Radial_D5.0mm_P2.00mm"),
    ("C", r"(?i)SNAP_IN_22", "Capacitor_THT:CP_Radial_D22.0mm_P10.00mm_SnapIn"),
    ("R", r"(?i)1005", "Resistor_SMD:R_0402_1005Metric"),
    ("R", r"(?i)2012", "Resistor_SMD:R_0805_2012Metric"),
    ("LED", r"(?i)C190", "LED_SMD:LED_0603_1608Metric"),
    ("D", r"(?i)0805", "LED_SMD:LED_0805_2012Metric"),
    ("D", r"(?i)^DO-214A$", "Diode_SMD:D_SMA"),
    ("D", r"(?i)^CGRM$", "Diode_SMD:D_SOD-123F"),
    ("D", r"(?i)SIP-4", "Diode_THT:Diode_Bridge_Vishay_KBPM"),
    ("Q", r"(?i)^SOT23$|SOT-23-3", "Package_TO_SOT_SMD:SOT-23"),
    ("Q", r"(?i)SOT-416", "Package_TO_SOT_SMD:SOT-323_SC-70"),
    ("U", r"(?i)^SOT23$", "Package_TO_SOT_SMD:SOT-23"),
    ("U", r"(?i)SOT23-5|SOT-23-5", "Package_TO_SOT_SMD:SOT-23-5"),
    ("U", r"(?i)^SOT-23-6$", "Package_TO_SOT_SMD:SOT-23-6"),
    ("U", r"(?i)THIN-6", "Package_TO_SOT_SMD:TSOT-23-6"),
    ("U", r"(?i)SOIC-28W", "Package_SO:SOIC-28W_7.5x17.9mm_P1.27mm"),
    ("U", r"(?i)TSSOP-28", "Package_SO:TSSOP-28_4.4x9.7mm_P0.65mm"),
    ("U", r"(?i)SOP65P640X120-16", "Package_SO:TSSOP-16_4.4x5mm_P0.65mm"),
    ("U", r"(?i)^SO8_L$", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm"),
    ("U", r"(?i)QFN-48", "Package_DFN_QFN:QFN-48-1EP_7x7mm_P0.5mm_EP5.15x5.15mm"),
    ("OPTO", r"(?i)SOP-4", "Package_SO:SOP-4_4.4x2.6mm_P1.27mm"),
    ("L", r"(?i)2520", "Inductor_SMD:L_1008_2520Metric"),
    ("L", r"(?i)XAL60", "Inductor_SMD:L_Coilcraft_XAL6060-XXX"),
    ("J", r"(?i)PINHEADER.*2X05", "Connector_PinHeader_1.27mm:PinHeader_2x05_P1.27mm_Vertical_SMD"),
    ("J", r"(?i)SMA_TH_VERTICAL", "Connector_Coaxial:SMA_Amphenol_132134_Vertical"),
    ("J", r"(?i)ESQ-103", "Connector_PinSocket_2.54mm:PinSocket_1x03_P2.54mm_Vertical"),
    ("SW", r"(?i)TS02", "Button_Switch_THT:SW_PUSH_6mm"),
    ("Y", r"(?i)SC20S", "Crystal:Crystal_SMD_2012-2Pin_2.0x1.2mm"),
    ("MDLE", r"(?i)RFM9", "RF_Module:HOPERF_RFM9XW_SMD"),
    ("MDLE", r"(?i)S2_-_MODULE", "RF_Module:HOPERF_RFM9XW_SMD"),
    ("MDLE", r"(?i)RASPBERRY", "Connector_PinSocket_2.54mm:PinSocket_2x20_P2.54mm_Vertical"),
]


def kicad_for(designator: str, footprint: str):
    prefix = re.sub(r"[^A-Z]", "", designator.split()[0].upper())
    for p, rx, target in _EXTRA + RULES:
        if prefix == p and re.search(rx, footprint):
            return target
    return None


def urls(target: str):
    lib, name = target.split(":")
    model = f"https://gitlab.com/kicad/libraries/kicad-packages3D/-/raw/master/{lib}.3dshapes/{name}.step"
    fp = f"https://gitlab.com/kicad/libraries/kicad-footprints/-/raw/master/{lib}.pretty/{name}.kicad_mod"
    return model, fp
