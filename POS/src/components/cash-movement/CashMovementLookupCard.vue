<template>
	<div class="rounded-xl border border-gray-200 bg-gray-50 p-4 space-y-4">
		<div v-if="movementType !== 'expense'">
			<label class="block text-xs font-semibold uppercase tracking-wide text-gray-500 mb-1">
				{{ movementType === 'customer' ? __('Customer') : __('Supplier') }}
			</label>
			<div class="relative">
				<input
					v-model="partySearchProxy"
					type="text"
					:placeholder="movementType === 'customer' ? __('Search customer...') : __('Search supplier...')"
					@focus="emit('focus-party')"
					@blur="emit('blur-party')"
					class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
				/>
				<div
					v-if="partyDropdownOpen && partyResults.length > 0"
					class="absolute left-0 right-0 top-full z-20 mt-1 overflow-hidden rounded-lg border border-gray-200 bg-white shadow-lg"
				>
					<button
						v-for="item in partyResults"
						:key="item.value"
						type="button"
						@mousedown.prevent="emit('select-party', item)"
						class="block w-full px-3 py-2 text-start text-sm hover:bg-blue-50"
					>
						<div class="font-medium text-gray-900">{{ item.value }}</div>
						<div v-if="item.description" class="text-xs text-gray-500">{{ item.description }}</div>
					</button>
				</div>
			</div>
			<div
				v-if="selectedParty"
				class="mt-2 inline-flex items-center gap-2 rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700"
			>
				{{ selectedParty }}
			</div>
			<div
				v-if="partyBalanceLoading"
				class="mt-3 rounded-lg border border-blue-100 bg-blue-50 px-3 py-3 text-sm text-blue-700"
			>
				{{ __('Loading balance...') }}
			</div>
			<div
				v-else-if="partyBalanceSummary"
				class="mt-3 rounded-lg border border-blue-100 bg-blue-50 px-3 py-3"
			>
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
			<div class="relative">
				<input
					v-model="expenseSearchProxy"
					type="text"
					:placeholder="expensePlaceholder"
					@focus="emit('focus-expense')"
					@blur="emit('blur-expense')"
					class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
				/>
				<div
					v-if="expenseDropdownOpen && expenseResults.length > 0"
					class="absolute left-0 right-0 top-full z-20 mt-1 overflow-hidden rounded-lg border border-gray-200 bg-white shadow-lg"
				>
					<button
						v-for="item in expenseResults"
						:key="item.name"
						type="button"
						@mousedown.prevent="emit('select-expense', item)"
						class="block w-full px-3 py-2 text-start text-sm hover:bg-emerald-50"
					>
						<div class="font-medium text-gray-900">{{ item.account_name || item.name }}</div>
						<div class="text-xs text-gray-500">{{ item.name }}</div>
					</button>
				</div>
			</div>
			<div v-if="expenseLoading" class="mt-3 rounded-lg border border-blue-100 bg-blue-50 px-3 py-3 text-sm text-blue-700">
				{{ __('Searching...') }}
			</div>
			<div
				v-if="selectedExpenseAccount"
				class="mt-2 inline-flex items-center gap-2 rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700"
			>
				{{ selectedExpenseAccount }}
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue"

const __ = window.__ || ((text) => text)

const props = defineProps({
	movementType: {
		type: String,
		default: "customer",
	},
	partySearch: {
		type: String,
		default: "",
	},
	partyResults: {
		type: Array,
		default: () => [],
	},
	partyDropdownOpen: {
		type: Boolean,
		default: false,
	},
	selectedParty: {
		type: String,
		default: "",
	},
	partyBalanceLoading: {
		type: Boolean,
		default: false,
	},
	partyBalanceSummary: {
		type: Object,
		default: null,
	},
	expenseSearch: {
		type: String,
		default: "",
	},
	expenseResults: {
		type: Array,
		default: () => [],
	},
	expenseDropdownOpen: {
		type: Boolean,
		default: false,
	},
	selectedExpenseAccount: {
		type: String,
		default: "",
	},
	expenseLoading: {
		type: Boolean,
		default: false,
	},
	expensePlaceholder: {
		type: String,
		default: "",
	},
	formatCurrency: {
		type: Function,
		required: true,
	},
})

const emit = defineEmits([
	"update:party-search",
	"focus-party",
	"blur-party",
	"select-party",
	"update:expense-search",
	"focus-expense",
	"blur-expense",
	"search-expense",
	"select-expense",
])

const partySearchProxy = computed({
	get: () => props.partySearch,
	set: (value) => emit("update:party-search", value),
})

const expenseSearchProxy = computed({
	get: () => props.expenseSearch,
	set: (value) => emit("update:expense-search", value),
})
</script>
