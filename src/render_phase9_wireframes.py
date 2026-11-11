"""Render five labeled Power BI layout blueprints; placeholders are not result charts."""
from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path(__file__).resolve().parents[1] / 'dashboard' / 'wireframes'
OUT.mkdir(parents=True, exist_ok=True)
PAGES = [
 ('01_executive_overview','NOVAMART Supply Chain Control Tower',
  ['Historical Units Sold','14-Day Forecast Units','Latest Inventory','Reorder SKUs','Critical Cases','Simulated On-Time %'],
  [('Historical demand trend · ACTUAL','Inventory status · SKU count'),('ABC portfolio · SKU count/value proxy','Management priority · case count'),('Location overview · sales / inventory / reorder','Data lineage and time-window notes')],
  'Location  |  Category'),
 ('02_demand_planning','Demand Planning & Forecast',
  ['Historical Units Sold','14-Day Forecast Units','Test MAE','Ridge Test WAPE','Baseline Test WAPE','SKU Variability'],
  [('ACTUAL / HISTORICAL · ends 2024-01-30','MODEL FORECAST · 2024-01-31 to 02-13'),('Demand by category · historical vs forecast','Demand by location · historical vs forecast'),('Forecast error by category / local SKU','SKU variability · CV table')],
  'Location  |  Category  |  Local SKU'),
 ('03_inventory_replenishment','Inventory Health & Replenishment',
  ['Latest Inventory','Reorder Required','Proposed Order Units','Avg Safety Stock','Avg Reorder Point','Snapshot 2024-01-30'],
  [('Inventory status · SKU count','Inventory vs reorder point · top 10'),('Proposed order quantities · top 10','Risk by category / location'),('Action table · SKU, inventory, forecast, policy, order','Policy assumptions / proposed orders note')],
  'Location  |  Category  |  Local SKU'),
 ('04_supplier_performance','Supplier Performance — Simulated Scenario',
  ['Simulated POs','Simulated On-Time %','Simulated Fill %','Avg Actual Lead Days','Relative Score','Scenario Only'],
  [('On-time delivery by supplier','Receipt fill by supplier'),('Lead-time variability by supplier','Relative score by supplier'),('Supplier table · PO, on-time, fill, delay, score, tier','SIMULATED procurement and supplier records')],
  'Supplier'),
 ('05_action_center','Supply Chain Action Center',
  ['Critical Cases','High Cases','A-Class Reorder','Needs Review Supplier Cases','Snapshot 2024-01-30','Proposed Actions'],
  [('Priority by category','Priority by simulated supplier tier'),('ACTION TABLE · SKU, ABC, inventory, ROP, forecast, qty, supplier, tier, priority','ACTION TABLE · continuation / scroll'),('Review demand, policy and supplier assumptions','No orders placed; supplier/procurement simulated')],
  'Priority  |  ABC Class  |  Location  |  Category  |  Supplier Tier')
]

def rect(x,y,w,h,fill='#FFFFFF',stroke='#D7E0EA',r=10):
 return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}"/>'
def label(x,y,s,size=17,color='#17324D',weight='normal'):
 return f'<text x="{x}" y="{y}" font-family="Arial,sans-serif" font-size="{size}" fill="{color}" font-weight="{weight}">{escape(s)}</text>'

for name,title,cards,panels,slicers in PAGES:
 parts=['<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720" role="img">',rect(0,0,1280,720,'#F5F7FA','#F5F7FA',0),rect(0,0,1280,80,'#17324D','#17324D',0),label(30,38,title,25,'#FFFFFF','bold'),label(30,62,'WIREFRAME / DESIGN BLUEPRINT — placeholder panels, no observed chart data',12,'#CBD5E1'),rect(26,92,1228,45),label(42,121,'SLICERS: '+slicers,15)]
 for i,card in enumerate(cards):
  x=26+i*205;parts.extend([rect(x,151,192,88),label(x+13,178,card,13,'#52667C','bold'),label(x+13,215,'KPI MEASURE',19,'#2970B2','bold')])
 for row,(left,right) in enumerate(panels):
  y=253+row*141; widths=(600,600) if row<2 else (780,420)
  x=26
  for j,text in enumerate((left,right)):
   w=widths[j];parts.extend([rect(x,y,w,128),label(x+16,y+27,text,16,'#17324D','bold'),label(x+16,y+64,'Visual / table area · see build guide for fields and filters',12,'#7890A6')]);x+=w+28
 footer='Published synthetic operations | Derived forecast and policy | Simulated supplier scenario'
 parts.extend([label(30,699,footer,12,'#52667C'),'</svg>'])
 (OUT/f'{name}.svg').write_text('\n'.join(parts)+'\n')
print('Created', len(PAGES), 'wireframes in',OUT)
