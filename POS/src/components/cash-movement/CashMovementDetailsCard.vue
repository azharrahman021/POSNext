<template>
	<div class="space-y-4">
		<div class="rounded-xl border border-gray-200 bg-white p-4">
			<label class="block text-xs font-semibold uppercase tracking-wide text-gray-500 mb-1">
				{{ __('Reference No') }}
			</label>
			<input
				v-model="referenceNoProxy"
				type="text"
				class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
			/>
		</div>

		<div class="rounded-xl border border-gray-200 bg-white p-4">
			<label class="block text-xs font-semibold uppercase tracking-wide text-gray-500 mb-1">
				{{ __('Reference Date') }}
			</label>
			<input
				v-model="referenceDateProxy"
				type="date"
				class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-100"
			/>
		</div>

		<div class="rounded-xl border border-gray-200 bg-white p-4">
			<label class="block text-xs font-semibold uppercase tracking-wide text-gray-500 mb-1">
				{{ __('Remarks') }}
			</label>
			<textarea
				v-model="remarksProxy"
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
</template>

<script setup>
import { computed } from "vue"

const __ = window.__ || ((text) => text)

const props = defineProps({
	referenceNo: {
		type: String,
		default: "",
	},
	referenceDate: {
		type: String,
		default: "",
	},
	remarks: {
		type: String,
		default: "",
	},
	movementLabel: {
		type: String,
		default: "",
	},
	amount: {
		type: Number,
		default: 0,
	},
	modeOfPayment: {
		type: String,
		default: "",
	},
	errorMessage: {
		type: String,
		default: "",
	},
	formatCurrency: {
		type: Function,
		required: true,
	},
})

const emit = defineEmits(["update:reference-no", "update:reference-date", "update:remarks"])

const referenceNoProxy = computed({
	get: () => props.referenceNo,
	set: (value) => emit("update:reference-no", value),
})

const referenceDateProxy = computed({
	get: () => props.referenceDate,
	set: (value) => emit("update:reference-date", value),
})

const remarksProxy = computed({
	get: () => props.remarks,
	set: (value) => emit("update:remarks", value),
})
</script>
