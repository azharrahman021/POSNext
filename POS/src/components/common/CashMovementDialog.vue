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
								<div v-if="partyBalanceLoading" class="mt-3 rounded-lg border border-blue-100 bg-blue-50 px-3 py-3 text-sm text-blue-700">
									{{ __('Loading balance...') }}
								</div>
								<div v-else-if="partyBalanceSummary" class="mt-3 rounded-lg border border-blue-100 bg-blue-50 px-3 py-3">
									<div class="text-xs font-semibold uppercase tracking-wide text-blue-600">
										{{ __('Balance Snapshot') }}
									</div>
									<div class="mt-2 space-y-2 text-sm">
										<div class="flex items-center justify-between gap-4">
											<span class="text-blue-700">{{ __('Current Company') }}</span>
											<span class="font-semibold text-blue-900">{{ formatCurrency(partyBalanceSummary.company_balance || 0) }}</span>
										</div>
										<div class="flex items-center justify-between gap-4">
											<span class="text-blue-700">{{ __('All Companies') }}</span>
											<span class="font-semibold text-blue-900">{{ formatCurrency(partyBalanceSummary.all_company_balance || 0) }}</span>
										</div>
									</div>
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

							<div
								v-if="movementType !== 'expense'"
								class="rounded-lg border border-amber-200 bg-amber-50 p-3 space-y-3"
							>
								<div class="flex items-center justify-between gap-3">
									<div>
										<div class="text-xs font-semibold uppercase tracking-wide text-amber-700">
											{{ __('Write Off') }}
										</div>
										<div class="text-xs text-amber-700/80">
											{{ selectedParty ? __('Use the switch to enable write off.') : __('Select a party to enable write off.') }}
										</div>
									</div>
									<button
										type="button"
										class="relative inline-flex h-8 w-14 items-center rounded-full border transition-colors duration-200"
										:class="applyWriteOff ? 'border-amber-500 bg-amber-500' : 'border-amber-300 bg-white'"
										@click="toggleWriteOff"
									>
										<span class="sr-only">{{ __('Toggle write off') }}</span>
										<span
											class="inline-block h-6 w-6 rounded-full bg-white shadow transition-transform duration-200"
											:class="applyWriteOff ? 'translate-x-6' : 'translate-x-1'"
										/>
									</button>
								</div>
								<div class="space-y-2">
									<div class="flex items-center justify-between text-[11px] text-amber-700/80">
										<span>{{ __('Off') }}</span>
										<span>{{ __('On') }}</span>
									</div>
									<div
										class="rounded-full border border-amber-300 bg-white px-4 py-2 text-xs font-semibold text-amber-700 transition-colors duration-200"
										:class="applyWriteOff ? 'bg-amber-50' : 'bg-white'"
									>
											{{ applyWriteOff ? __('Write Off Enabled') : __('Write Off Disabled') }}
										</div>
								</div>
								<div class="flex items-center justify-between gap-4 text-sm">
									<span class="text-amber-700">{{ __('Remaining to Write Off') }}</span>
									<span class="font-semibold text-amber-900">{{ formatCurrency(writeOffAmount || 0) }}</span>
								</div>
								<div v-if="!selectedParty" class="text-xs text-amber-700/80">
									{{ __('Write off is available after selecting a customer or supplier.') }}
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
import { parseError } from "@/utils/errorHandler"
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
	writeOffAccount: {
		type: String,
		default: "",
	},
	writeOffCostCenter: {
		type: String,
		default: "",
	},
	writeOffLimit: {
		type: Number,
		default: 0,
	},
})

const emit = defineEmits(["update:modelValue", "saved"])

const { showSuccess, showError, showWarning } = useToast()

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
const partyBalanceSummary = ref(null)
const partyBalanceLoading = ref(false)

const expenseSearch = ref("")
const expenseResults = ref([])
const expenseDropdownOpen = ref(false)
const selectedExpenseAccount = ref("")
const expenseAutoSelecting = ref(false)
const applyWriteOff = ref(false)

let partyTimer = null
let expenseTimer = null

const movementLabel = computed(() => {
	if (movementType.value === "supplier") return __("Supplier Payment")
	if (movementType.value === "expense") return __("Expense")
	return __("Customer Payment")
})

const partyCompanyBalance = computed(() => {
	return Number(partyBalanceSummary.value?.company_balance || 0)
})

const partyOutstanding = computed(() => {
	return Math.abs(partyCompanyBalance.value)
})

const writeOffAmount = computed(() => {
	if (movementType.value === "expense" || !applyWriteOff.value) return 0
	return Math.max(partyOutstanding.value - Number(amount.value || 0), 0)
})

const submitLabel = computed(() => {
	if (movementType.value === "expense") return __("Submit")
	return __("Submit")
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
	partyBalanceSummary.value = null
	partyBalanceLoading.value = false
	expenseSearch.value = ""
	expenseResults.value = []
	selectedExpenseAccount.value = ""
	applyWriteOff.value = false
	movementType.value = "customer"
	if (paymentMethods.value.length > 0) {
		const defaultMethod = paymentMethods.value.find((method) => method.default)
		modeOfPayment.value = defaultMethod?.mode_of_payment || paymentMethods.value[0].mode_of_payment
	}
}

function resetWriteOffSlider() {
	applyWriteOff.value = false
}

function canToggleWriteOff() {
	if (!selectedParty.value) {
		showWarning(__("Select a party first"))
		return false
	}
	if (partyBalanceLoading.value) {
		showWarning(__("Party balance is still loading"))
		return false
	}
	if (!props.writeOffAccount) {
		showWarning(__("Write off account is not configured for this POS profile"))
		return false
	}
	if (partyOutstanding.value <= 0) {
		showWarning(__("No party balance available to write off"))
		return false
	}
	if (props.writeOffLimit > 0 && writeOffAmount.value > props.writeOffLimit) {
		showWarning(
			__("Write off amount cannot exceed {0}", [
				formatCurrency(props.writeOffLimit),
			]),
		)
		return false
	}
	return true
}

function toggleWriteOff() {
	if (!applyWriteOff.value) {
		if (!canToggleWriteOff()) return
		applyWriteOff.value = true
		return
	}
	applyWriteOff.value = false
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

async function loadPartyBalance(partyName) {
	if (!partyName || movementType.value === "expense") {
		partyBalanceSummary.value = null
		return
	}

	partyBalanceLoading.value = true
	try {
		const result = await call("pos_next.api.cash_movements.get_party_balance_summary", {
			company: props.company,
			party_type: movementType.value === "supplier" ? "Supplier" : "Customer",
			party: partyName,
			posting_date: postingDate.value,
			cost_center: defaults.value.cost_center || "",
		})
		partyBalanceSummary.value = result?.message || result || null
	} catch (error) {
		partyBalanceSummary.value = null
	} finally {
		partyBalanceLoading.value = false
	}
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
		score: row.score || 0,
	}))

	const normalizedQuery = (query || "").trim().toLowerCase()
	const topMatch = expenseResults.value[0]
	if (
		!expenseAutoSelecting.value &&
		movementType.value === "expense" &&
		topMatch &&
		normalizedQuery.length >= 3 &&
		topMatch.score >= 90 &&
		(topMatch.score >= (expenseResults.value[1]?.score || 0) + 15 || expenseResults.value.length === 1)
	) {
		expenseAutoSelecting.value = true
		selectExpenseAccount(topMatch)
		setTimeout(() => {
			expenseAutoSelecting.value = false
		}, 0)
	}
}

function selectParty(item) {
	selectedParty.value = item.value
	partySearch.value = item.value
	partyDropdownOpen.value = false
	partyResults.value = []
	applyWriteOff.value = false
	loadPartyBalance(item.value).catch(() => {})
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
	partyBalanceSummary.value = null
	partyBalanceLoading.value = false
	expenseSearch.value = defaults.value.default_expense_account || ""
	selectedExpenseAccount.value = defaults.value.default_expense_account || ""
	resetWriteOffSlider()
})

watch(partySearch, (value) => {
	if (value !== selectedParty.value) {
		selectedParty.value = ""
		partyBalanceSummary.value = null
		resetWriteOffSlider()
	}
	clearTimeout(partyTimer)
	partyTimer = setTimeout(() => {
		partyDropdownOpen.value = true
		searchParties(value).catch(() => {
			partyResults.value = []
		})
	}, 250)
})

watch(postingDate, () => {
	if (selectedParty.value) {
		loadPartyBalance(selectedParty.value).catch(() => {})
	}
})

watch([amount, selectedParty, movementType], () => {
	if (movementType.value === "expense") {
		applyWriteOff.value = false
		return
	}
	if (!selectedParty.value) {
		applyWriteOff.value = false
		return
	}
})

watch(expenseSearch, (value) => {
	if (movementType.value !== "expense") return
	if (expenseAutoSelecting.value) return
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
			write_off_amount: movementType.value !== "expense" && applyWriteOff.value ? Number(writeOffAmount.value || 0) : 0,
			write_off_account: movementType.value !== "expense" && applyWriteOff.value ? props.writeOffAccount : "",
			write_off_cost_center: movementType.value !== "expense" && applyWriteOff.value ? (props.writeOffCostCenter || defaults.value.cost_center || "") : "",
		}

		const result = await call("pos_next.api.cash_movements.create_cash_movement", payload)
		const data = result?.message || result || {}
		showSuccess(__("{0} created: {1}", [movementLabel.value, data.name || ""]))
		emit("saved", data)
		show.value = false
	} catch (error) {
		const parsed = parseError(error)
		errorMessage.value = parsed.message || error.message || __("Failed to save movement")
		showError(__("Unable to save movement"), errorMessage.value)
	} finally {
		submitting.value = false
	}
}
</script>
