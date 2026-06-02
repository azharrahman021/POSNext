# Item Rack Location Management

## Purpose

POSNext can already show the preferred picking shelf on item cards and can switch
the sale warehouse when the default shelf is short. This enhancement adds the
missing management facility inside POS so authorized users can create or update
the rack-location rule for an item without leaving the POS workflow.

## Where The Feature Belongs

- POS item browser in `Start POS`
- Stock-item cards only
- Visible only to users who can create or write `POS Item Location Rule`

The feature edits the existing `POS Item Location Rule` record when that doctype
is available on the site. POSNext does not create a second storage model for rack
locations.

## Expected Behavior

1. A user with rack-location permissions can open a location editor from an item card.
2. POS loads the current rule for the item and company.
3. The user can set:
   - default shelf warehouse
   - optional short display label
   - enabled state
   - alternate shelf warehouses with labels and priority
4. Saving updates the existing rule or creates it if it does not exist yet.
5. After save, the POS item card reflects the updated default location label.

## User Workflow

1. Open `Start POS`.
2. Find a stock item in the item grid or list.
3. Click the rack-location action on the item card.
4. Choose the default shelf warehouse for the item.
5. Optionally add a short label like `A1-R3`.
6. Optionally add alternate shelves in fallback priority order.
7. Save.

## Edge Cases

- If the site does not have `POS Item Location Rule`, the editor stays unavailable.
- If the user lacks permission, the action is hidden and backend writes are blocked.
- Default and alternate rows cannot point to the same warehouse.
- Group warehouses are rejected by the underlying doctype validation.
- Cross-company warehouses are rejected by the underlying doctype validation.
- If no rule exists yet, save creates the first rule for that item and company.
- Existing ERPNext row-level warehouse choices remain untouched until the item is
  added to a sale and the normal location-resolution flow runs.

## Configuration And Setup

- The site must already provide the `POS Item Location Rule` doctype.
- Warehouse options come from leaf warehouses in the current company.
- No extra POSNext setting is required.

## Implementation Notes

- Backend API: `pos_next.api.item_locations`
- POS UI entry point: `POS/src/components/sale/ItemsSelector.vue`
- The feature is intentionally additive and does not change invoice submission,
  stock deduction, or warehouse-availability behavior outside rack-location edits.
