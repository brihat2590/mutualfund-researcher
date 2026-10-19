export class InvestmentInputError extends RangeError {
    constructor(message, field = null) {
        super(message);
        this.name = "InvestmentInputError";
        this.field = field;
    }
}

export function calculateInvestmentGrowth({ type, amount, annualReturn, years }) {
    if (type !== "sip" && type !== "lump-sum") {
        throw new InvestmentInputError("Choose Monthly SIP or Lump sum.", "type");
    }
    if (!Number.isFinite(amount) || amount <= 0) {
        throw new InvestmentInputError("Enter an investment amount greater than zero.", "amount");
    }
    if (!Number.isFinite(annualReturn) || annualReturn <= -100) {
        throw new InvestmentInputError("Enter an annual return greater than -100%.", "annualReturn");
    }
    if (!Number.isSafeInteger(years) || years < 1 || !Number.isSafeInteger(years * 12)) {
        throw new InvestmentInputError("Enter a duration in whole years, starting from 1.", "years");
    }

    const annualRate = annualReturn / 100;
    const months = years * 12;
    const totalInvested = type === "sip" ? amount * months : amount;
    let futureValue;

    if (annualRate === 0) {
        futureValue = totalInvested;
    } else if (type === "sip") {
        const monthlyRate = annualRate / 12;
        // An ordinary annuity: each contribution arrives at the end of the month.
        // log1p/expm1 avoid cancellation when the assumed return is close to zero.
        futureValue = amount * (Math.expm1(months * Math.log1p(monthlyRate)) / monthlyRate);
    } else {
        futureValue = amount * Math.exp(years * Math.log1p(annualRate));
    }

    if (![totalInvested, futureValue].every(value => Number.isFinite(value) && value <= Number.MAX_SAFE_INTEGER)) {
        throw new InvestmentInputError("These inputs exceed the calculator's numeric range. Reduce the amount, return or duration.");
    }

    return { futureValue, totalInvested, estimatedGains: futureValue - totalInvested };
}
