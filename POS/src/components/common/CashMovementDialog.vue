<template>
	<Dialog
		v-model="show"
		:options="{ title: __('Payments & Expenses'), size: 'xl' }"
	>
		<template #body-content>
			<div class="space-y-4">
				<div class="flex flex-wrap gap-2">
					<button
						v-for="tab in tabs"
						:key="tab.key"
						type="button"
						@click="movementType = tab.key"
						:class="[
							'px-4 py-2 rounded-lg border text-sm font-semibold transition-colors',
							movementType === tab.key
								? tab.activeClass
								: 'bg-white border-gray-200 text-gray-600 hover:border-gray-300'
						]"
					>
						{{ __(tab.label) }}
					</button>
				</div>

				<div class="grid gap-4 lg:grid-cols-2">
					<div class="space-y-4">
						<div class="rounded-xl border border-gray-200 bg-gray-50 p-4 space-y-4">
							<div>
								<label class="block text-xs font-semibold uppercase tracking-wide text-gray-500 mb-1">
									{{ __('Posting Date') }}
								</label>
								<input
									v-model="postingDate"
									type="date"
									class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
								/>
							</div>

							<div>
								<label class="block text-xs font-semibold uppercase tracking-wide text-gray-500 mb-1">
									{{ __('Mode of Payment') }}
								</label>
								<select
									v-model="modeOfPayment"
									class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
								>
									<option v-for="method in paymentMethods" :key="method.mode_of_payment" :value="method.mode_of_payment">
										{{ method.mode_of_payment }}
									</option>
								</select>
							</div>

							<div>
								<label class="block text-xs font-semibold uppercase tracking-wide text-gray-500 mb-1">
									{{ __('Amount') }}
								</label>
								<input
									v-model.number="amount"
									type="number"
									min="0"
									step="0.01"
									class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
								/>
							</div>

							<div v-if="movementType !== 'expense'">
								<label class="block text-xs font-semibold uppercase tracking-wide text-gray-500 mb-1">
									{{ movementType === 'customer' ? __('Customer') : __('Supplier') }}
								</label>
								<input
									v-model="partySearch"
									type="text"
									:placeholder="movementType === 'customer' ? __('Search customer...') : __('Search supplier...')"
									@focus="partyDropdownOpen = true"
									@blur="handlePartyBlur"
									class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
								/>
								<div
									v-if="partyDropdownOpen && partyResults.length > 0"
									class="relative z-20"
								>
									<div class="absolute mt-1 w-full overflow-hidden rounded-lg border border-gray-200 bg-white shadow-lg">
										<button
											v-for="item in partyResults"
											:key="item.value"
											type="button"
											@mousedown.prevent="selectParty(item)"
											class="block w-full px-3 py-2 text-start text-sm hover:bg-blue-50"
										>
											<div class="font-medium text-gray-900">{{ item.value }}</div>
											<div v-if="item.description" class="text-xs text-gray-500">{{ item.description }}</div>
										</button>
									</div>
								</div>
								<div v-if="selectedParty" class="mt-2 inline-flex items-center gap-2 rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">
									{{ selectedParty }}
								</div>
							</div>

							<div v-else>
								<label class="block text-xs font-semibold uppercase tracking-wide text-gray-500 mb-1">
									{{ __('Expense Account') }}
								</label>
								<input
									v-model="expenseSearch"
									type="text"
									:placeholder="defaults.default_expense_account || __('Search expense account...')"
									@focus="expenseDropdownOpen = true"
									@blur="handleExpenseBlur"
									class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
								/>
								<div
									v-if="expenseDropdownOpen && expenseResults.length > 0"
									class="relative z-20"
								>
									<div class="absolute mt-1 w-full overflow-hidden rounded-lg border border-gray-200 bg-white shadow-lg">
										<button
											v-for="item in expenseResults"
											:key="item.name"
											type="button"
											@mousedown.prevent="selectExpenseAccount(item)"
											class="block w-full px-3 py-2 text-start text-sm hover:bg-emerald-50"
										>
											<div class="font-medium text-gray-900">{{ item.account_name || item.name }}</div>
											<div class="text-xs text-gray-500">{{ item.name }}</div>
										</button>
									</div>
								</div>
								<div v-if="selectedExpenseAccount" class="mt-2 inline-flex items-center gap-2 rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
									{{ selectedExpenseAccount }}
								</div>
							</div>
						</div>
					</div>

					<div class="space-y-4">
						<div class="rounded-xl border border-gray-200 bg-white p-4">
							<label class="block text-xs font-semibold uppercase tracking-wide text-gray-500 mb-1">
								{{ __('Reference No') }}
							</label>
							<input
								v-model="referenceNo"
								type="text"
								class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
							/>
						</div>

						<div class="rounded-xl border border-gray-200 bg-white p-4">
							<label class="block text-xs font-semibold uppercase tracking-wide text-gray-500 mb-1">
								{{ __('Remarks') }}
							</label>
							<textarea
								v-model="remarks"
								rows="5"
								class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
							/>
						</div>

						<div class="rounded-xl border border-dashed border-gray-300 bg-gray-50 p-4">
							<div class="text-xs font-semibold uppercase tracking-wide text-gray-500">{{ __('Summary') }}</div>
							<div class="mt-3 space-y-2 text-sm">
								<div class="flex items-center justify-between">
									<span class="text-gray-600">{{ __('Type') }}</span>
									<span class="font-semibold text-gray-900">{{ movementLabel }}</span>
								</div>
								<div class="flex items-center justify-between">
									<span class="text-gray-600">{{ __('Amount') }}</span>
									<span class="font-semibold text-gray-900">{{ formatCurrency(amount || 0) }}</span>
								</div>
								<div class="flex items-center justify-between">
									<span class="text-gray-600">{{ __('Mode') }}</span>
									<span class="font-semibold text-gray-900">{{ modeOfPayment || __('Not set') }}</span>
								</div>
							</div>
						</div>

						<div v-if="errorMessage" class="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
							{{ errorMessage }}
						</div>
					</div>
				</div>
			</div>
		</template>

		<template #actions>
			<div class="flex w-full gap-2">
				<Button variant="subtle" class="flex-1" @click="show = false">
					{{ __('Close') }}
				</Button>
				<Button
					variant="solid"
					theme="blue"
					class="flex-1"
					:loading="submitting"
					:disabled="!canSubmit"
					@click="submitMovement"
				>
					{{ submitLabel }}
				</Button>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { Button, call } from "frappe-ui"
import { computed, ref, watch } from "vue"
import { useToast } from "@/composables/useToast"
import { formatCurrency as formatCurrencyUtil } from "@/utils/currency"

const props = defineProps({
	modelValue: Boolean,
	posProfile: {
		type: String,
		default: "",
	},
	company: {
		type: String,
		default: "",
	},
	currency: {
		type: String,
		default: "USD",
	},
})

const emit = defineEmits(["update:modelValue", "saved"])

const { showSuccess, showError } = useToast()

const show = computed({
	get: () => props.modelValue,
	set: (value) => emit("update:modelValue", value),
})

const tabs = [
	{ key: "customer", label: "Customer Payment", activeClass: "bg-blue-500 border-blue-500 text-white" },
	{ key: "supplier", label: "Supplier Payment", activeClass: "bg-orange-500 border-orange-500 text-white" },
	{ key: "expense", label: "Expense", activeClass: "bg-emerald-500 border-emerald-500 text-white" },
]

const movementType = ref("customer")
const postingDate = ref(new Date().toISOString().slice(0, 10))
const amount = ref(0)
const modeOfPayment = ref("")
const referenceNo = ref("")
const remarks = ref("")
const submitting = ref(false)
const errorMessage = ref("")

const paymentMethods = ref([])
const defaults = ref({})

const partySearch = ref("")
const partyResults = ref([])
const partyDropdownOpen = ref(false)
const selectedParty = ref("")

const expenseSearch = ref("")
const expenseResults = ref([])
const expenseDropdownOpen = ref(false)
const selectedExpenseAccount = ref("")

let partyTimer = null
let expenseTimer = null

const movementLabel = computed(() => {
	if (movementType.value === "supplier") return __("Supplier Payment")
	if (movementType.value === "expense") return __("Expense")
	return __("Customer Payment")
})

const submitLabel = computed(() => {
	if (movementType.value === "expense") return __("Record Expense")
	return __("Save Payment")
})

const canSubmit = computed(() => {
	if (!props.posProfile || !props.company) return false
	if (!modeOfPayment.value || Number(amount.value) <= 0) return false
	if (movementType.value === "expense") {
		return Boolean(selectedExpenseAccount.value || expenseSearch.value.trim())
	}
	return Boolean(selectedParty.value || partySearch.value.trim())
})

function formatCurrency(amountValue) {
	return formatCurrencyUtil(Number(amountValue || 0), props.currency)
}

function resetForm() {
	postingDate.value = new Date().toISOString().slice(0, 10)
	amount.value = 0
	referenceNo.value = ""
	remarks.value = ""
	errorMessage.value = ""
	partySearch.value = ""
	partyResults.value = []
	selectedParty.value = ""
	expenseSearch.value = ""
	expenseResults.value = []
	selectedExpenseAccount.value = ""
	movementType.value = "customer"
	if (paymentMethods.value.length > 0) {
		const defaultMethod = paymentMethods.value.find((method) => method.default)
		modeOfPayment.value = defaultMethod?.mode_of_payment || paymentMethods.value[0].mode_of_payment
	}
}

async function loadDefaults() {
	if (!props.company) return

	try {
		const result = await call("pos_next.api.cash_movements.get_cash_movement_defaults", {
			company: props.company,
		})
		defaults.value = result?.message || result || {}
		expenseSearch.value = defaults.value.default_expense_account || ""
		selectedExpenseAccount.value = defaults.value.default_expense_account || ""
	} catch (error) {
		defaults.value = {}
	}
}

async function loadPaymentMethods() {
	if (!props.posProfile) return

	try {
		const result = await call("pos_next.api.pos_profile.get_payment_methods", {
			pos_profile: props.posProfile,
		})
		paymentMethods.value = result?.message || result || []
		if (paymentMethods.value.length > 0 && !modeOfPayment.value) {
			const defaultMethod = paymentMethods.value.find((method) => method.default)
			modeOfPayment.value = defaultMethod?.mode_of_payment || paymentMethods.value[0].mode_of_payment
		}
	} catch (error) {
		paymentMethods.value = []
	}
}

async function searchParties(query) {
	if (!query.trim()) {
		partyResults.value = []
		return
	}

	const doctype = movementType.value === "supplier" ? "Supplier" : "Customer"
	const result = await call("frappe.desk.search.search_link", {
		doctype,
		txt: query,
		page_length: 10,
	})
	const rows = result?.message || result || []
	partyResults.value = rows.map((row) => ({
		value: row.value || row.name || row,
		description: row.description || row.extra || "",
	}))
}

async function searchExpenseAccounts(query) {
	const result = await call("pos_next.api.cash_movements.search_expense_accounts", {
		company: props.company,
		txt: query || "",
		page_length: 10,
	})
	const rows = result?.message || result || []
	expenseResults.value = rows.map((row) => ({
		name: row.name,
		account_name: row.account_name,
	}))
}

function selectParty(item) {
	selectedParty.value = item.value
	partySearch.value = item.value
	partyDropdownOpen.value = false
	partyResults.value = []
}

function selectExpenseAccount(item) {
	selectedExpenseAccount.value = item.name
	expenseSearch.value = item.name
	expenseDropdownOpen.value = false
	expenseResults.value = []
}

function handlePartyBlur() {
	setTimeout(() => {
		partyDropdownOpen.value = false
	}, 150)
}

function handleExpenseBlur() {
	setTimeout(() => {
		expenseDropdownOpen.value = false
	}, 150)
}

watch(
	() => show.value,
	async (open) => {
		errorMessage.value = ""
		if (!open) {
			resetForm()
			return
		}

		await Promise.all([loadDefaults(), loadPaymentMethods()])
		resetForm()
	},
)

watch(movementType, () => {
	errorMessage.value = ""
	partySearch.value = ""
	partyResults.value = []
	selectedParty.value = ""
	expenseSearch.value = defaults.value.default_expense_account || ""
	selectedExpenseAccount.value = defaults.value.default_expense_account || ""
})

watch(partySearch, (value) => {
	if (value !== selectedParty.value) {
		selectedParty.value = ""
	}
	clearTimeout(partyTimer)
	partyTimer = setTimeout(() => {
		partyDropdownOpen.value = true
		searchParties(value).catch(() => {
			partyResults.value = []
		})
	}, 250)
})

watch(expenseSearch, (value) => {
	if (movementType.value !== "expense") return
	if (value !== selectedExpenseAccount.value) {
		selectedExpenseAccount.value = ""
	}
	clearTimeout(expenseTimer)
	expenseTimer = setTimeout(() => {
		expenseDropdownOpen.value = true
		searchExpenseAccounts(value).catch(() => {
			expenseResults.value = []
		})
	}, 250)
})

async function submitMovement() {
	errorMessage.value = ""
	submitting.value = true

	try {
		const payload = {
			pos_profile: props.posProfile,
			company: props.company,
			movement_type: movementType.value,
			amount: Number(amount.value),
			mode_of_payment: modeOfPayment.value,
			posting_date: postingDate.value,
			reference_no: referenceNo.value.trim(),
			remarks: remarks.value.trim(),
			party_type: movementType.value === "customer" ? "Customer" : movementType.value === "supplier" ? "Supplier" : null,
			party: movementType.value === "expense" ? null : (selectedParty.value || partySearch.value.trim()),
			expense_account: movementType.value === "expense" ? (selectedExpenseAccount.value || expenseSearch.value.trim()) : null,
			cost_center: defaults.value.cost_center || "",
		}

		const result = await call("pos_next.api.cash_movements.create_cash_movement", payload)
		const data = result?.message || result || {}
		showSuccess(__("{0} created: {1}", [movementLabel.value, data.name || ""]))
		emit("saved", data)
		show.value = false
	} catch (error) {
		errorMessage.value = error.message || __("Failed to save movement")
		showError(__("Unable to save movement"), errorMessage.value)
	} finally {
		submitting.value = false
	}
}
</script>
