import { logger } from "@/utils/logger"

const log = logger.create("AndroidBluetoothPrinter")

const PRINTER_ADDRESS_KEY = "pos_android_bluetooth_printer_address"

function getPlugin() {
	return window?.Capacitor?.Plugins?.PosBluetoothPrinter || null
}

export function isAndroidBluetoothPrinterAvailable() {
	return Boolean(getPlugin())
}

export function getSavedAndroidPrinterAddress() {
	try {
		return localStorage.getItem(PRINTER_ADDRESS_KEY) || ""
	} catch {
		return ""
	}
}

export function saveAndroidPrinterAddress(address) {
	try {
		localStorage.setItem(PRINTER_ADDRESS_KEY, address || "")
	} catch (error) {
		log.warn("Failed to save Android printer address:", error)
	}
}

export async function findAndroidPrinters() {
	const plugin = getPlugin()
	if (!plugin) return []

	const result = await plugin.listPairedPrinters()
	return result?.printers || []
}

function encodeBase64(bytes) {
	let binary = ""
	const chunkSize = 0x8000
	for (let i = 0; i < bytes.length; i += chunkSize) {
		const chunk = bytes.subarray(i, i + chunkSize)
		binary += String.fromCharCode(...chunk)
	}
	return btoa(binary)
}

function textBytes(text) {
	return Array.from(new TextEncoder().encode(text))
}

function command(...bytes) {
	return bytes
}

function line(text = "") {
	return textBytes(`${text}\n`)
}

function money(value) {
	return Number.parseFloat(value || 0).toFixed(2)
}

function truncate(text, width) {
	const value = String(text || "")
	return value.length > width ? value.slice(0, Math.max(0, width - 1)) : value
}

function twoColumn(left, right, width = 42) {
	const leftText = String(left || "")
	const rightText = String(right || "")
	const space = Math.max(1, width - leftText.length - rightText.length)
	return `${truncate(leftText, width - rightText.length - 1)}${" ".repeat(space)}${rightText}`
}

function divider(width = 42) {
	return "-".repeat(width)
}

function derivePaidAmount(invoiceData) {
	if (invoiceData.paid_amount != null) return invoiceData.paid_amount
	if (!Array.isArray(invoiceData.payments)) return 0
	return invoiceData.payments.reduce(
		(sum, payment) => sum + (Number.parseFloat(payment.amount) || 0),
		0,
	)
}

export function buildEscPosReceiptBytes(invoiceData) {
	const bytes = []
	const items = Array.isArray(invoiceData.items) ? invoiceData.items : []
	const payments = Array.isArray(invoiceData.payments) ? invoiceData.payments : []
	const paidAmount = derivePaidAmount(invoiceData)

	bytes.push(...command(0x1b, 0x40)) // Initialize
	bytes.push(...command(0x1b, 0x61, 0x01)) // Center
	bytes.push(...command(0x1b, 0x45, 0x01)) // Bold on
	bytes.push(...line(invoiceData.company || "POS Next"))
	bytes.push(...command(0x1b, 0x45, 0x00))
	bytes.push(...line(invoiceData.header || "TAX INVOICE"))
	bytes.push(...line())

	bytes.push(...command(0x1b, 0x61, 0x00)) // Left
	bytes.push(...line(twoColumn("Invoice:", invoiceData.name || "")))
	bytes.push(...line(twoColumn("Date:", invoiceData.posting_date || new Date().toISOString().slice(0, 10))))
	if (invoiceData.customer_name || invoiceData.customer) {
		bytes.push(...line(twoColumn("Customer:", invoiceData.customer_name || invoiceData.customer)))
	}
	if (invoiceData.is_offline) {
		bytes.push(...line("OFFLINE - PENDING SYNC"))
	}
	bytes.push(...line(divider()))

	for (const item of items) {
		const name = item.item_name || item.item_code || ""
		const qty = item.quantity || item.qty || 0
		const rate = item.price_list_rate || item.rate || 0
		const amount = qty * rate
		bytes.push(...line(truncate(name, 42)))
		bytes.push(...line(twoColumn(`${qty} x ${money(rate)}`, money(amount))))

		if (item.discount_amount || item.discount_percentage) {
			const label = item.discount_percentage
				? `Discount (${Number(item.discount_percentage).toFixed(2)}%)`
				: "Discount"
			bytes.push(...line(twoColumn(label, `-${money(item.discount_amount || 0)}`)))
		}
		if (item.serial_no) {
			bytes.push(...line(`Serial: ${String(item.serial_no).replace(/\n/g, ", ")}`))
		}
	}

	bytes.push(...line(divider()))
	if (invoiceData.total_taxes_and_charges > 0) {
		bytes.push(...line(twoColumn("Subtotal:", money((invoiceData.grand_total || 0) - invoiceData.total_taxes_and_charges))))
		bytes.push(...line(twoColumn("Tax:", money(invoiceData.total_taxes_and_charges))))
	}
	if (invoiceData.discount_amount) {
		bytes.push(...line(twoColumn("Additional Discount:", `-${money(Math.abs(invoiceData.discount_amount))}`)))
	}

	bytes.push(...command(0x1b, 0x45, 0x01))
	bytes.push(...line(twoColumn("TOTAL:", money(invoiceData.grand_total))))
	bytes.push(...command(0x1b, 0x45, 0x00))

	if (payments.length) {
		bytes.push(...line(divider()))
		bytes.push(...line("Payments:"))
		for (const payment of payments) {
			bytes.push(...line(twoColumn(`${payment.mode_of_payment || "Payment"}:`, money(payment.amount))))
		}
		bytes.push(...line(twoColumn("Total Paid:", money(paidAmount))))
		if (invoiceData.change_amount > 0) {
			bytes.push(...line(twoColumn("Change:", money(invoiceData.change_amount))))
		}
		if (invoiceData.outstanding_amount > 0) {
			bytes.push(...line(twoColumn("BALANCE DUE:", money(invoiceData.outstanding_amount))))
		}
	}

	bytes.push(...line(divider()))
	bytes.push(...command(0x1b, 0x61, 0x01))
	bytes.push(...line(invoiceData.footer || "Thank you for your business!"))
	bytes.push(...line())
	bytes.push(...line())
	bytes.push(...line())
	bytes.push(...command(0x1d, 0x56, 0x42, 0x00)) // Partial cut

	return new Uint8Array(bytes)
}

export async function printInvoiceOnAndroid(invoiceData, printerAddress = null) {
	const plugin = getPlugin()
	if (!plugin) throw new Error("Android Bluetooth printer bridge is not available")

	let address = printerAddress || getSavedAndroidPrinterAddress()
	if (!address) {
		const printers = await findAndroidPrinters()
		if (printers.length === 1) {
			address = printers[0].address
			saveAndroidPrinterAddress(address)
		}
	}
	if (!address) {
		throw new Error("No Android Bluetooth printer selected")
	}

	const bytes = buildEscPosReceiptBytes(invoiceData)
	await plugin.printRawBase64({
		address,
		data: encodeBase64(bytes),
	})
	return true
}

export async function openAndroidCashDrawer(printerAddress = null) {
	const plugin = getPlugin()
	if (!plugin) throw new Error("Android Bluetooth printer bridge is not available")

	let address = printerAddress || getSavedAndroidPrinterAddress()
	if (!address) {
		const printers = await findAndroidPrinters()
		if (printers.length === 1) {
			address = printers[0].address
			saveAndroidPrinterAddress(address)
		}
	}
	if (!address) {
		throw new Error("No Android Bluetooth printer selected")
	}

	await plugin.printRawBase64({
		address,
		data: encodeBase64(new Uint8Array([0x1b, 0x70, 0x00, 0x19, 0xfa])),
	})
	return true
}
