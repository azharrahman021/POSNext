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

				<div v-else-if="errorMessage" class="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
					{{ errorMessage }}
				</div>

				<div v-else class="space-y-4">
					<label class="flex items-center gap-2 text-sm text-gray-700">
						<input v-model="form.enabled" type="checkbox" class="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500" />
						<span>{{ __('Enable rack location rule') }}</span>
					</label>

					<div class="grid gap-4 sm:grid-cols-2">
						<div>
							<label class="mb-1 block text-xs font-medium text-gray-600">{{ __('Default Shelf Warehouse') }}</label>
							<select
								v-model="form.default_warehouse"
								class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
							>
								<option value="">{{ __('Select warehouse') }}</option>
								<option
									v-for="option in warehouseOptions"
									:key="option.value"
									:value="option.value"
								>
									{{ option.label }} ({{ option.value }})
								</option>
							</select>
						</div>
						<div>
							<label class="mb-1 block text-xs font-medium text-gray-600">{{ __('Display Label') }}</label>
							<input
								v-model="form.display_label"
								type="text"
								class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
								:placeholder="__('Optional short label like A1-R3')"
							/>
						</div>
					</div>

					<div class="space-y-2">
						<div class="flex items-center justify-between">
							<h4 class="text-sm font-semibold text-gray-900">{{ __('Alternate Shelf Locations') }}</h4>
							<button
								type="button"
								@click="addAlternateRow"
								class="rounded-md border border-blue-200 bg-blue-50 px-2.5 py-1.5 text-xs font-semibold text-blue-700 hover:bg-blue-100"
							>
								{{ __('Add Alternate') }}
							</button>
						</div>

						<div v-if="form.alternate_locations.length === 0" class="rounded-lg border border-dashed border-gray-200 px-3 py-4 text-center text-xs text-gray-500">
							{{ __('No alternate shelves configured.') }}
						</div>

						<div
							v-for="(location, index) in form.alternate_locations"
							:key="index"
							class="grid gap-2 rounded-lg border border-gray-200 bg-white p-3 sm:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)_100px_44px]"
						>
							<select
								v-model="location.warehouse"
								class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
							>
								<option value="">{{ __('Select warehouse') }}</option>
								<option
									v-for="option in warehouseOptions"
									:key="`${index}-${option.value}`"
									:value="option.value"
								>
									{{ option.label }} ({{ option.value }})
								</option>
							</select>
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
								@click="removeAlternateRow(index)"
								class="rounded-lg border border-red-200 bg-red-50 px-2 py-2 text-sm font-semibold text-red-700 hover:bg-red-100"
								:aria-label="__('Remove alternate location')"
							>
								×
							</button>
						</div>
					</div>

					<p class="text-xs text-gray-500">
						{{ __('Use leaf warehouses only. Default and alternate rows cannot point to the same shelf.') }}
					</p>
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
					@click="save"
					:disabled="loading || saving || !form.default_warehouse"
				>
					{{ saving ? __('Saving...') : __('Save Rack Location') }}
				</Button>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { Button, Dialog } from "frappe-ui"
import { computed, ref, watch } from "vue"
import { call } from "@/utils/apiWrapper"
import { useToast } from "@/composables/useToast"

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
		display_label: "",
		alternate_locations: [],
	}
}

function addAlternateRow() {
	form.value.alternate_locations.push({
		warehouse: "",
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
			default_warehouse: rule.default_warehouse || "",
			display_label: rule.display_label || "",
			alternate_locations: (rule.alternate_locations || []).map((row) => ({
				warehouse: row.warehouse || "",
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
					form.value.alternate_locations || [],
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
