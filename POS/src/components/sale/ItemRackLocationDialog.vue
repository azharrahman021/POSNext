<template>
	<Dialog v-model="isOpen" :options="{ title: __('Manage Rack Location'), size: 'lg' }">
		<template #body-content>
			<div class="space-y-4 py-3">
				<div v-if="item" class="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2">
					<p class="text-sm font-semibold text-gray-900">{{ item.item_name }}</p>
					<p class="text-xs text-gray-500">{{ item.item_code }}</p>
				</div>

				<div v-if="loading" class="flex items-center justify-center py-10">
					<div class="h-8 w-8 animate-spin rounded-full border-b-2 border-blue-500"></div>
					<p class="ms-3 text-sm text-gray-500">{{ __('Loading rack location...') }}</p>
				</div>

				<div
					v-else-if="errorMessage"
					class="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
				>
					{{ errorMessage }}
				</div>

				<div v-else class="space-y-4">
					<label class="flex items-center gap-2 text-sm text-gray-700">
						<input
							v-model="form.enabled"
							type="checkbox"
							class="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
						/>
						<span>{{ __('Enabled') }}</span>
					</label>

					<div class="grid gap-4 sm:grid-cols-2">
						<div>
							<label class="mb-1 block text-xs font-medium text-gray-600">
								{{ __('Default Shelf Warehouse') }}
							</label>
							<div class="relative">
								<input
									v-model="form.default_warehouse_query"
									type="text"
									class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
									:placeholder="__('Search warehouse or rack label')"
									@focus="openPicker('default', form, 'default_warehouse_query', 'default_warehouse', $event)"
									@input="handleWarehouseInput(form, 'default_warehouse_query', 'default_warehouse', 'default')"
									@blur="closePicker(form, 'default_warehouse_query', 'default_warehouse')"
								/>
								<LocationOptions
									v-if="activePicker === 'default'"
									:options="filteredWarehouseOptions(form.default_warehouse_query)"
									@select="selectWarehouse(form, $event, 'default_warehouse', 'default_warehouse_query')"
								/>
							</div>
						</div>

						<div>
							<label class="mb-1 block text-xs font-medium text-gray-600">
								{{ __('Default Display Label') }}
							</label>
							<input
								v-model="form.display_label"
								type="text"
								class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
								:placeholder="__('Example: A1-R3')"
							/>
						</div>
					</div>

					<div class="space-y-2">
						<div class="flex items-center justify-between gap-3">
							<h4 class="text-sm font-semibold text-gray-900">
								{{ __('Alternate Shelf Locations') }}
							</h4>
							<button
								type="button"
								class="rounded-md border border-blue-200 bg-blue-50 px-2.5 py-1.5 text-xs font-semibold text-blue-700 hover:bg-blue-100"
								@click="addAlternateRow"
							>
								{{ __('Add Alternate') }}
							</button>
						</div>

						<div
							v-if="form.alternate_locations.length === 0"
							class="rounded-lg border border-dashed border-gray-200 px-3 py-4 text-center text-xs text-gray-500"
						>
							{{ __('No alternate shelf locations added.') }}
						</div>

						<div
							v-for="(location, index) in form.alternate_locations"
							:key="index"
							class="grid gap-2 rounded-lg border border-gray-200 bg-white p-3 sm:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)_90px_40px]"
						>
							<div class="relative">
								<input
									v-model="location.warehouse_query"
									type="text"
									class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
									:placeholder="__('Search warehouse')"
									@focus="openPicker(`alternate-${index}`, location, 'warehouse_query', 'warehouse', $event)"
									@input="handleWarehouseInput(location, 'warehouse_query', 'warehouse', `alternate-${index}`)"
									@blur="closePicker(location, 'warehouse_query', 'warehouse')"
								/>
								<LocationOptions
									v-if="activePicker === `alternate-${index}`"
									:options="filteredWarehouseOptions(location.warehouse_query)"
									@select="selectWarehouse(location, $event, 'warehouse', 'warehouse_query')"
								/>
							</div>
							<input
								v-model="location.display_label"
								type="text"
								class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
								:placeholder="__('Label')"
							/>
							<input
								v-model.number="location.priority"
								type="number"
								min="1"
								step="1"
								class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
								:placeholder="__('Priority')"
							/>
							<button
								type="button"
								class="rounded-lg border border-red-200 bg-red-50 px-2 py-2 text-sm font-semibold text-red-700 hover:bg-red-100"
								:aria-label="__('Remove alternate location')"
								@click="removeAlternateRow(index)"
							>
								×
							</button>
						</div>
					</div>
				</div>
			</div>
		</template>

		<template #actions>
			<div class="flex w-full gap-2">
				<Button class="flex-1" variant="subtle" @click="isOpen = false">
					{{ __('Cancel') }}
				</Button>
				<Button
					class="flex-1"
					variant="solid"
					theme="blue"
					:disabled="loading || saving || !form.default_warehouse"
					@click="save"
				>
					{{ saving ? __('Saving...') : __('Save') }}
				</Button>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { Button, Dialog } from "frappe-ui"
import { computed, ref, watch } from "vue"
import { useToast } from "@/composables/useToast"
import { call } from "@/utils/apiWrapper"

const props = defineProps({
	modelValue: Boolean,
	item: {
		type: Object,
		default: null,
	},
	company: {
		type: String,
		default: "",
	},
})

const emit = defineEmits(["update:modelValue", "saved"])
const { showSuccess, showWarning } = useToast()

const loading = ref(false)
const saving = ref(false)
const errorMessage = ref("")
const warehouseOptions = ref([])
const activePicker = ref("")
const form = ref(emptyForm())

const isOpen = computed({
	get: () => props.modelValue,
	set: (value) => emit("update:modelValue", value),
})

watch(
	() => [props.modelValue, props.item?.item_code, props.company],
	([open]) => {
		if (open) {
			loadConfig()
		}
	},
)

function emptyForm() {
	return {
		enabled: true,
		default_warehouse: "",
		default_warehouse_query: "",
		display_label: "",
		alternate_locations: [],
	}
}

function normalizeOption(option) {
	const label = option.display_label || option.label || option.value
	return {
		...option,
		label,
		subtitle: option.value === label ? "" : option.value,
	}
}

const normalizedWarehouseOptions = computed(() =>
	warehouseOptions.value.map(normalizeOption),
)

function normalizeSearchText(value) {
	return String(value || "")
		.toLowerCase()
		.replace(/[^a-z0-9]+/g, " ")
		.trim()
}

function matchesWarehouseOption(option, query) {
	const search = normalizeSearchText(query)
	if (!search) return true

	const haystack = normalizeSearchText(
		[option.label, option.subtitle, option.value, option.display_label].join(
			" ",
		),
	)
	const compactHaystack = haystack.replace(/\s+/g, "")
	const compactSearch = search.replace(/\s+/g, "")
	const tokens = search.split(/\s+/).filter(Boolean)

	return (
		haystack.includes(search) ||
		compactHaystack.includes(compactSearch) ||
		tokens.every((token) => haystack.includes(token))
	)
}

function filteredWarehouseOptions(query) {
	const options = normalizedWarehouseOptions.value
	return options
		.filter((option) => matchesWarehouseOption(option, query))
		.slice(0, 30)
}

function getOptionDisplay(option) {
	return option?.display_label || option?.label || option?.value || ""
}

function getSelectedWarehouseDisplay(row, valueField) {
	const selected = normalizedWarehouseOptions.value.find(
		(option) => option.value === row?.[valueField],
	)
	return (
		getOptionDisplay(selected) || row?.display_label || row?.[valueField] || ""
	)
}

function getWarehouseQuery(row, queryField, valueField) {
	if (row?.[queryField]) {
		return row[queryField]
	}

	return getSelectedWarehouseDisplay(row, valueField)
}

function selectWarehouse(row, option, valueField, queryField) {
	row[valueField] = option.value
	row[queryField] = getOptionDisplay(option)
	if (!row.display_label) {
		row.display_label = getOptionDisplay(option)
	}
	activePicker.value = ""
}

function openPicker(picker, row, queryField, valueField, event) {
	activePicker.value = picker
	row[queryField] = ""
	event?.target?.select?.()
}

function handleWarehouseInput(row, queryField, valueField, picker) {
	activePicker.value = picker
	if (
		normalizeSearchText(row?.[queryField]) !==
		normalizeSearchText(getSelectedWarehouseDisplay(row, valueField))
	) {
		row[valueField] = ""
	}
}

function closePicker(row, queryField, valueField) {
	window.setTimeout(() => {
		if (!row[queryField] && row[valueField]) {
			row[queryField] = getWarehouseQuery(row, queryField, valueField)
		}
		activePicker.value = ""
	}, 120)
}

function addAlternateRow() {
	form.value.alternate_locations.push({
		warehouse: "",
		warehouse_query: "",
		display_label: "",
		priority: (form.value.alternate_locations.length + 1) * 100,
	})
}

function removeAlternateRow(index) {
	form.value.alternate_locations.splice(index, 1)
}

async function loadConfig() {
	if (!props.item?.item_code || !props.company) {
		errorMessage.value = __("Item and company are required.")
		return
	}

	loading.value = true
	errorMessage.value = ""
	form.value = emptyForm()
	warehouseOptions.value = []

	try {
		const response = await call(
			"pos_next.api.item_locations.get_item_rack_location_config",
			{
				item_code: props.item.item_code,
				company: props.company,
			},
		)
		const payload = response?.message || response || {}
		const rule = payload.rule || {}

		warehouseOptions.value = payload.warehouse_options || []
		form.value = {
			enabled: Boolean(rule.enabled ?? true),
			default_warehouse:
				rule.default_warehouse ||
				props.item?.pos_current_warehouse ||
				props.item?.pos_rack_warehouse ||
				props.item?.pos_location_warehouse ||
				"",
			default_warehouse_query:
				rule.display_label ||
				props.item?.pos_current_location ||
				props.item?.pos_rack_label ||
				props.item?.pos_location_label ||
				rule.default_warehouse ||
				props.item?.pos_current_warehouse ||
				props.item?.pos_rack_warehouse ||
				props.item?.pos_location_warehouse ||
				"",
			display_label:
				rule.display_label ||
				props.item?.pos_current_location ||
				props.item?.pos_rack_label ||
				props.item?.pos_location_label ||
				"",
			alternate_locations: (rule.alternate_locations || []).map((row) => ({
				warehouse: row.warehouse || "",
				warehouse_query: row.display_label || row.warehouse || "",
				display_label: row.display_label || "",
				priority: Number.parseInt(row.priority || 100, 10),
			})),
		}
	} catch (error) {
		console.error("Failed to load rack location config", error)
		errorMessage.value =
			error?.messages?.[0] ||
			error?.message ||
			__("Could not load rack location settings.")
	} finally {
		loading.value = false
	}
}

async function save() {
	if (!form.value.default_warehouse) {
		showWarning(__("Default shelf warehouse is required."))
		return
	}

	saving.value = true
	try {
		const response = await call(
			"pos_next.api.item_locations.upsert_item_rack_location_config",
			{
				item_code: props.item.item_code,
				company: props.company,
				default_warehouse: form.value.default_warehouse,
				display_label: form.value.display_label || "",
				alternate_locations: JSON.stringify(
					(form.value.alternate_locations || []).map((row) => ({
						warehouse: row.warehouse || "",
						display_label: row.display_label || "",
						priority: row.priority,
					})),
				),
				enabled: form.value.enabled ? 1 : 0,
			},
		)
		const payload = response?.message || response || {}
		showSuccess(payload.message || __("Rack location updated."))
		emit("saved", payload.rule || null)
		isOpen.value = false
	} catch (error) {
		console.error("Failed to save rack location config", error)
		showWarning(
			error?.messages?.[0] ||
				error?.message ||
				__("Could not save rack location settings."),
		)
	} finally {
		saving.value = false
	}
}
</script>

<script>
export default {
	components: {
		LocationOptions: {
			props: {
				options: {
					type: Array,
					default: () => [],
				},
			},
			emits: ["select"],
			template: `
				<div class="absolute z-30 mt-1 max-h-64 w-full overflow-y-auto rounded-lg border border-gray-200 bg-white shadow-xl">
					<button
						v-for="option in options"
						:key="option.value"
						type="button"
						class="block w-full border-b border-gray-100 px-3 py-2 text-left text-sm hover:bg-blue-50"
						@mousedown.prevent="$emit('select', option)"
					>
						<span class="block font-medium text-gray-900">{{ option.label }}</span>
						<span v-if="option.subtitle" class="block text-xs text-gray-500">{{ option.subtitle }}</span>
					</button>
					<div v-if="options.length === 0" class="px-3 py-3 text-sm text-gray-500">
						No matching warehouse found.
					</div>
				</div>
			`,
		},
	},
}
</script>
