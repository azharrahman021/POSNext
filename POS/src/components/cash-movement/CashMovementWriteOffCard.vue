<template>
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
				@click="emit('toggle')"
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
		<div
			v-if="!selectedParty"
			class="text-xs text-amber-700/80"
		>
			{{ __('Write off is available after selecting a customer or supplier.') }}
		</div>
	</div>
</template>

<script setup>
const __ = window.__ || ((text) => text)

defineProps({
	movementType: {
		type: String,
		default: "customer",
	},
	applyWriteOff: {
		type: Boolean,
		default: false,
	},
	selectedParty: {
		type: String,
		default: "",
	},
	writeOffAmount: {
		type: Number,
		default: 0,
	},
	formatCurrency: {
		type: Function,
		required: true,
	},
})

const emit = defineEmits(["toggle"])
</script>
