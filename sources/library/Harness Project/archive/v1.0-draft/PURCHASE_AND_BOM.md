# Purchase/BOM State — 2026-09-30

## Current GPU candidate

User-provided Newegg listing:

https://www.newegg.com/msi-rtx-3060/p/1FT-0009-00B46

Resolved listing details on 2026-09-30:

- Product: MSI RTX 3060 Ventus 2X OC 12GB
- Condition: refurbished
- Current displayed price: $359.99 each
- Seller: QYTech
- Ships from: Canada
- Newegg page shows free 30-day returns
- Listing states the card was manufacturer-refurbished by MSI
- Accessories: card only
- This is a marketplace seller listing, not a current "Sold by Newegg" offer

Three at the displayed price: **$1,079.97 before tax**.

Historical Newegg-sold refurb page for the same Ventus 2X model showed **$249.99** but is currently out of stock. Therefore $359.99 should not be treated as an unusually strong price merely because the page is on Newegg.

## Exact 3060 mechanical/electrical facts

MSI manufacturer spec for GeForce RTX 3060 Ventus 2X 12G OC:

- 12GB GDDR6
- PCIe Gen4
- 3584 CUDA cores
- 170W
- one 8-pin auxiliary connector
- 235 × 124 × 42 mm
- 675 g

## Quantity plan

- Buy/build initial population: 3 cards
- Chassis/links: design for 4 positions
- Empty position: preserved and blanked for airflow

## Remaining hardware selections

Still TBD before final purchase release:

1. PCI_E1 x16-to-4×x4 bifurcation host adapter
2. Four matched high-speed cables
3. Four remote x16 mechanically/full-height locally powered receiver slots
4. Exact 1000 W external PSU SKU and native cable inventory
5. Two 120 mm high-static-pressure fans
6. RTX 5070 Ti external extension/receiver hardware for PCI_E4 x4
7. Fasteners / heat-set inserts / vibration pads
8. Chassis filament and spool strategy after slicer mass estimate

## Purchase gates

Do not bulk-buy link hardware until the exact host splitter and receiver system is documented for x4/x4/x4/x4 passive bifurcation. Do not substitute a PLX/switch board unless deliberately reverting to the older shared-switch architecture.
