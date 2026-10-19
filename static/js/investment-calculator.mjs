import { calculateInvestmentGrowth, InvestmentInputError } from "./investment-growth.mjs";

const form = document.getElementById("investmentForm");
const amountInput = document.getElementById("investmentAmount");
const returnInput = document.getElementById("investmentReturn");
const yearsInput = document.getElementById("investmentYears");
const amountLabel = document.getElementById("investmentAmountLabel");
const assumptions = document.getElementById("investmentAssumptions");
const results = document.getElementById("investmentResults");
const futureValueOutput = document.getElementById("investmentFutureValue");
const totalOutput = document.getElementById("investmentTotal");
const gainsOutput = document.getElementById("investmentGains");
const resultNote = document.getElementById("investmentResultNote");
const errorMessage = document.getElementById("calculatorError");
const calculateButton = document.getElementById("calculateGrowthBtn");
const fundName = document.getElementById("investmentFundName");
const minimumNote = document.getElementById("investmentMinimumNote");
const returnNote = document.getElementById("investmentReturnNote");
let selectedFundName = "";
let minimumSip = null;
const currency = new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
});

function clearError() {
    errorMessage.hidden = true;
    errorMessage.textContent = "";
    form.querySelectorAll('[aria-invalid="true"]').forEach(input => input.removeAttribute("aria-invalid"));
    delete calculateButton.dataset.state;
}

function resetResults() {
    results.dataset.state = "empty";
    [futureValueOutput, totalOutput, gainsOutput].forEach(output => { output.textContent = "\u2014"; });
    gainsOutput.classList.remove("text-positive", "text-negative");
    resultNote.textContent = "Select Calculate growth to update your estimate.";
}

function updateInvestmentMode() {
    const isSip = form.querySelector('input[name="type"]:checked').value === "sip";
    amountLabel.textContent = isSip ? "Monthly investment (\u20b9)" : "One-time investment (\u20b9)";
    amountInput.min = isSip && minimumSip !== null ? String(minimumSip) : "0.01";
    minimumNote.textContent = isSip
        ? (minimumSip !== null
            ? `This fund's minimum monthly SIP is ${currency.format(minimumSip)}. You can invest more.`
            : "Minimum SIP is not available for this fund. Enter your planned monthly amount.")
        : "Enter your one-time amount. This fund's lump-sum minimum is not available here.";
    assumptions.textContent = isSip
        ? "SIP assumes equal month-end contributions. Monthly return = annual return \u00f7 12."
        : "Lump sum assumes one investment at the start, compounded annually.";
}

document.getElementById("fundModal").addEventListener("fund-analysis-open", event => {
    const fund = event.detail;
    selectedFundName = fund.fund_name;
    fundName.textContent = `${selectedFundName} \u00b7 Scheme code: ${fund.scode}`;
    minimumSip = Number.isFinite(fund.min_sip_amount) && fund.min_sip_amount > 0
        ? fund.min_sip_amount : null;
    const rollingMean = fund.rolling_stats?.mean;
    const hasRollingReturn = fund.rolling_stats?.observation_count > 0
        && Number.isFinite(rollingMean) && rollingMean > -100;

    form.reset();
    clearError();
    resetResults();
    amountInput.value = minimumSip !== null ? String(minimumSip) : "";
    returnInput.value = hasRollingReturn ? String(rollingMean) : "";
    returnNote.textContent = hasRollingReturn
        ? `Historical reference: this fund's average 5-year rolling CAGR is ${rollingMean}%. Used as an editable starting assumption, not a forecast or historical SIP return.`
        : "No usable 5-year rolling return is available for this fund. Enter your own annual return assumption.";
    updateInvestmentMode();
    calculateButton.disabled = false;
});

form.addEventListener("input", () => {
    clearError();
    if (results.dataset.state === "success") resetResults();
});

form.addEventListener("change", event => {
    if (event.target.name !== "type") return;
    clearError();
    resetResults();
    updateInvestmentMode();
});

form.addEventListener("submit", event => {
    event.preventDefault();
    clearError();
    const type = form.querySelector('input[name="type"]:checked').value;

    try {
        if (!selectedFundName) {
            throw new InvestmentInputError("Select a fund from the research results before calculating.");
        }
        const invalidInput = [amountInput, returnInput, yearsInput].find(input => !input.validity.valid);
        if (invalidInput) {
            throw new InvestmentInputError(
                `${invalidInput.labels[0].textContent}: ${invalidInput.validationMessage}`,
                invalidInput.name
            );
        }

        const estimate = calculateInvestmentGrowth({
            type,
            amount: amountInput.valueAsNumber,
            annualReturn: returnInput.valueAsNumber,
            years: yearsInput.valueAsNumber
        });
        const formatAmount = value => currency.format(Math.abs(value) < 0.005 ? 0 : value);
        futureValueOutput.textContent = formatAmount(estimate.futureValue);
        totalOutput.textContent = formatAmount(estimate.totalInvested);
        gainsOutput.textContent = formatAmount(estimate.estimatedGains);
        gainsOutput.classList.toggle("text-positive", estimate.estimatedGains >= 0.005);
        gainsOutput.classList.toggle("text-negative", estimate.estimatedGains <= -0.005);
        const schedule = type === "sip"
            ? `${(yearsInput.valueAsNumber * 12).toLocaleString("en-IN")} month-end contributions`
            : "One initial investment";
        resultNote.textContent = `${selectedFundName}: ${schedule} over ${yearsInput.value} years at ${returnInput.value}% assumed annual return.`
            + (estimate.estimatedGains < -0.005 ? " Negative gains represent an estimated loss." : "");
        results.dataset.state = "success";
        calculateButton.dataset.state = "success";
    } catch (error) {
        if (!(error instanceof InvestmentInputError)) throw error;
        resetResults();
        errorMessage.textContent = error.message;
        errorMessage.hidden = false;
        calculateButton.dataset.state = "error";
        const invalidInput = error.field ? form.querySelector(`[name="${error.field}"]`) : null;
        if (invalidInput) {
            invalidInput.setAttribute("aria-invalid", "true");
            invalidInput.focus();
        } else {
            errorMessage.focus();
        }
    }
});
