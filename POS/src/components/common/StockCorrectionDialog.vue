<template>
	<Dialog
		v-model="show"
		:options="{ title: __('Stock Correction'), size: '2xl' }"
	>
		<template #body-content>
			<div class="grid gap-4 lg:grid-cols-2">
				<div class="space-y-3">
					<div>
						<label class="block text-xs font-semibold uppercase tracking-wide text-gray-500 mb-1">
							{{ __('Item') }}
						</label>
						<input
							v-model="searchText"
							type="text"
							:placeholder="__('Search item code or name')"
							class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-cyan-500 focus:outline-none focus:ring-2 focus:ring-cyan-100"
						/>
					</div>

					<div class="min-h-[360px] rounded-lg border border-gray-200 bg-gray-50 p-2">
						<div v-if="loading" class="py-12 text-center text-sm text-gray-500">
							{{ __('Searching...') }}
						</div>
						<div v-else-if="!items.length" class="py-12 text-center text-sm text-gray-500">
							{{ __('No matching item found') }}
						</div>
						<div v-else class="space-y-2">
							<button
								v-for="item in items"
								:key="item.item_code"
								type="button"
								class="w-full rounded-lg border bg-white p-3 text-left transition-colors"
								:class="selectedItem?.item_code === item.item_code ? 'border-cyan-500 ring-2 ring-cyan-100' : 'border-gray-200 hover:border-cyan-300'"
								@click="selectItem(item)"
							>
								<div class="flex items-start justify-between gap-3">
									<div class="min-w-0">
										<div class="truncate text-sm font-semibold text-gray-900">
											{{ item.item_name || item.item_code }}
										</div>
										<div class="truncate text-xs text-gray-500">
											{{ item.item_code }}
										</div>
									</div>
									<div class="shrink-0 rounded-md bg-cyan-50 px-2 py-1 text-right">
										<div class="text-[11px] font-medium uppercase text-cyan-700">
											{{ __('Karanthad') }}
										</div>
										<div class="text-sm font-semibold text-cyan-900">
											{{ formatQty(item.target_qty) }} {{ item.stock_uom }}
										</div>
									</div>
								</div>
								<div class="mt-2 text-xs text-gray-500">
									{{ __('Palakode') }}: {{ formatQty(item.source_qty) }} {{ item.stock_uom }}
								</div>
							</button>
						</div>
					</div>
				</div>

				<div class="rounded-lg border border-gray-200 bg-white p-4 min-w-0">
					<div v-if="!selectedItem" class="flex h-full min-h-[360px] items-center justify-center text-center text-sm text-gray-500">
						{{ __('Select an item to increase stock') }}
					</div>
					<div v-else class="space-y-4">
						<div class="min-w-0 rounded-lg border border-gray-100 bg-gray-50 px-3 py-2">
							<div class="break-words text-base font-semibold leading-snug text-gray-900">
								{{ selectedItem.item_name || selectedItem.item_code }}
							</div>
							<div class="mt-1 break-all text-xs text-gray-500">
								{{ selectedItem.item_code }}
							</div>
						</div>

						<div class="grid grid-cols-2 gap-3">
							<div class="rounded-lg bg-cyan-50 p-3">
								<div class="text-xs font-medium uppercase text-cyan-700">
									{{ __('Existing Stock') }}
								</div>
								<div class="mt-1 text-lg font-semibold text-cyan-950">
									{{ formatQty(selectedItem.target_qty) }}
								</div>
								<div class="text-xs text-cyan-700">{{ selectedItem.stock_uom }}</div>
							</div>
							<div class="rounded-lg bg-emerald-50 p-3">
								<div class="text-xs font-medium uppercase text-emerald-700">
									{{ __('After Submit') }}
								</div>
								<div class="mt-1 text-lg font-semibold text-emerald-950">
									{{ formatQty(nextTargetQty) }}
								</div>
								<div class="text-xs text-emerald-700">{{ selectedItem.stock_uom }}</div>
							</div>
						</div>

						<div>
							<label class="block text-xs font-semibold uppercase tracking-wide text-gray-500 mb-1">
								{{ __('Unit') }}
							</label>
							<select
								v-model="selectedUom"
								class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-cyan-500 focus:outline-none focus:ring-2 focus:ring-cyan-100"
							>
								<option
									v-for="uomOption in uomOptions"
									:key="uomOption.uom"
									:value="uomOption.uom"
								>
									{{ uomOption.uom }}
								</option>
							</select>
							<div v-if="selectedConversionFactor !== 1" class="mt-1 text-xs text-gray-500">
								{{ __('1 {0} = {1} {2}', [selectedUom, formatQty(selectedConversionFactor), selectedItem.stock_uom]) }}
							</div>
						</div>

						<div>
							<label class="block text-xs font-semibold uppercase tracking-wide text-gray-500 mb-1">
								{{ __('Increase Quantity') }}
							</label>
							<div class="rounded-lg border border-gray-200 bg-gray-50 p-3">
								<div class="mb-3 text-center text-3xl font-semibold text-gray-900">
									{{ formatQty(increaseQty) }} <span class="text-base font-medium text-gray-500">{{ selectedUom }}</span>
								</div>
								<div class="grid grid-cols-3 gap-2">
									<Button variant="subtle" @click="addQty(1)">+1</Button>
									<Button variant="subtle" @click="addQty(5)">+5</Button>
									<Button variant="subtle" @click="addQty(10)">+10</Button>
								</div>
								<input
									v-model.number="manualQty"
									type="number"
									min="0"
									step="1"
									:placeholder="__('Enter extra quantity')"
									class="mt-3 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-cyan-500 focus:outline-none focus:ring-2 focus:ring-cyan-100"
								/>
								<div class="mt-2 text-xs text-gray-600">
									{{ __('Stock Qty') }}: {{ formatQty(increaseStockQty) }} {{ selectedItem.stock_uom }}
								</div>
							</div>
						</div>

						<div>
							<label class="block text-xs font-semibold uppercase tracking-wide text-gray-500 mb-1">
								{{ __('Remarks') }}
							</label>
							<textarea
								v-model="remarks"
								rows="3"
								class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-cyan-500 focus:outline-none focus:ring-2 focus:ring-cyan-100"
							/>
						</div>

						<div v-if="errorMessage" class="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
							{{ errorMessage }}
						</div>
						<div v-if="successResult" class="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
							<div>{{ __('Sales Invoice') }}: {{ successResult.sales_invoice }}</div>
							<div>{{ __('Purchase Invoice') }}: {{ successResult.purchase_invoice }}</div>
						</div>
					</div>
				</div>
			</div>
		</template>

		<template #actions>
			<div class="flex w-full gap-2">
				<Button variant="subtle" class="flex-1" @click="closeDialog">
					{{ __('Close') }}
				</Button>
				<Button
					variant="solid"
					theme="blue"
					class="flex-1"
					:loading="submitting"
					:disabled="!canSubmit"
					@click="submitIncrease"
				>
					{{ __('Create Transfer') }}
				</Button>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { Button, call } from "frappe-ui"
import { computed, ref, watch } from "vue"
import { useToast } from "@/composables/useToast"
import { parseError } from "@/utils/errorHandler"

const props = defineProps({
	modelValue: Boolean,
	posProfile: {
		type: String,
		default: "",
	},
})

const emit = defineEmits(["update:modelValue", "saved"])

const { showSuccess, showError } = useToast()

const show = computed({
	get: () => props.modelValue,
	set: (value) => emit("update:modelValue", value),
})

const searchText = ref("")
const items = ref([])
const selectedItem = ref(null)
const increaseQty = ref(0)
const manualQty = ref(null)
const selectedUom = ref("")
const remarks = ref("")
const loading = ref(false)
const submitting = ref(false)
const errorMessage = ref("")
const successResult = ref(null)

let searchTimer = null

const nextTargetQty = computed(() => {
	return Number(selectedItem.value?.target_qty || 0) + increaseStockQty.value
})

const uomOptions = computed(() => {
	if (!selectedItem.value) return []
	const options = Array.isArray(selectedItem.value.item_uoms) ? selectedItem.value.item_uoms : []
	if (options.length) return options
	return [{ uom: selectedItem.value.stock_uom, conversion_factor: 1 }]
})

const selectedConversionFactor = computed(() => {
	const option = uomOptions.value.find((row) => row.uom === selectedUom.value)
	return Number(option?.conversion_factor || 1)
})

const increaseStockQty = computed(() => {
	return Number(increaseQty.value || 0) * selectedConversionFactor.value
})

const canSubmit = computed(() => {
	return Boolean(props.posProfile && selectedItem.value?.item_code && Number(increaseQty.value) > 0)
})

watch(show, (value) => {
	if (value) {
		searchItems()
	} else {
		resetDialog()
	}
})

watch(searchText, () => {
	clearTimeout(searchTimer)
	searchTimer = setTimeout(() => {
		searchItems()
	}, 250)
})

watch(manualQty, (value) => {
	const qty = Number(value || 0)
	increaseQty.value = qty > 0 ? qty : 0
})

function formatQty(value) {
	return Number(value || 0).toLocaleString(undefined, {
		minimumFractionDigits: 0,
		maximumFractionDigits: 3,
	})
}

function resetDialog() {
	searchText.value = ""
	items.value = []
	selectedItem.value = null
	increaseQty.value = 0
	manualQty.value = null
	selectedUom.value = ""
	remarks.value = ""
	errorMessage.value = ""
	successResult.value = null
	submitting.value = false
}

function closeDialog() {
	show.value = false
}

async function searchItems() {
	if (!show.value || !props.posProfile) return

	loading.value = true
	errorMessage.value = ""
	try {
		const result = await call("pos_next.api.stock_corrections.search_stock_correction_items", {
			pos_profile: props.posProfile,
			txt: searchText.value,
			page_length: 20,
		})
		items.value = Array.isArray(result) ? result : []
	} catch (error) {
		errorMessage.value = parseError(error)
		showError(errorMessage.value)
	} finally {
		loading.value = false
	}
}

function selectItem(item) {
	selectedItem.value = item
	increaseQty.value = 0
	manualQty.value = null
	selectedUom.value = item.stock_uom
	errorMessage.value = ""
	successResult.value = null
}

function addQty(qty) {
	increaseQty.value = Number(increaseQty.value || 0) + qty
	manualQty.value = increaseQty.value
}

async function submitIncrease() {
	if (!canSubmit.value || submitting.value) return

	submitting.value = true
	errorMessage.value = ""
	successResult.value = null
	try {
		const result = await call("pos_next.api.stock_corrections.create_stock_increase_transfer", {
			pos_profile: props.posProfile,
			item_code: selectedItem.value.item_code,
			qty: increaseQty.value,
			uom: selectedUom.value,
			remarks: remarks.value,
		})
		successResult.value = result
		selectedItem.value = {
			...selectedItem.value,
			target_qty: result.target_qty,
			source_qty: result.source_qty,
		}
		increaseQty.value = 0
		manualQty.value = null
		showSuccess(__("Stock transfer created"))
		emit("saved", result)
		await searchItems()
	} catch (error) {
		errorMessage.value = parseError(error)
		showError(errorMessage.value)
	} finally {
		submitting.value = false
	}
}
</script>
