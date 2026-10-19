import test from "node:test";
import assert from "node:assert/strict";
import { calculateInvestmentGrowth, InvestmentInputError } from "../static/js/investment-growth.mjs";

const defaults = { type: "sip", amount: 5000, annualReturn: 12, years: 10 };
const calculate = overrides => calculateInvestmentGrowth({ ...defaults, ...overrides });
const closeTo = (actual, expected) => assert.ok(Math.abs(actual - expected) < 0.005, `${actual} != ${expected}`);

test("monthly SIP returns future value, total contributions and gains", () => {
    const result = calculate({});
    closeTo(result.futureValue, 1150193.45);
    assert.equal(result.totalInvested, 600000);
    closeTo(result.estimatedGains, 550193.45);
});

test("lump sum compounds one investment annually", () => {
    const result = calculate({ type: "lump-sum", amount: 100000 });
    closeTo(result.futureValue, 310584.82);
    assert.equal(result.totalInvested, 100000);
    closeTo(result.estimatedGains, 210584.82);
});

for (const type of ["sip", "lump-sum"]) {
    test(`${type}: zero return leaves principal unchanged`, () => {
        const result = calculate({ type, annualReturn: 0 });
        assert.equal(result.futureValue, type === "sip" ? 600000 : 5000);
        assert.equal(result.futureValue, result.totalInvested);
        assert.equal(result.estimatedGains, 0);
    });

    test(`${type}: fractional amounts and negative returns`, () => {
        const result = calculate({ type, amount: 1000.25, annualReturn: -12, years: 2 });
        assert.ok(result.futureValue > 0);
        assert.ok(result.estimatedGains < 0);
        closeTo(result.totalInvested, type === "sip" ? 24006 : 1000.25);
        closeTo(result.futureValue, type === "sip" ? 21437.54480122604 : 774.5936);
    });

    test(`${type}: very small returns do not lose the principal through cancellation`, () => {
        const result = calculate({ type, annualReturn: 1e-12 });
        closeTo(result.futureValue, result.totalInvested);
    });
}

test("SIP matches month-by-month, end-of-month contributions", () => {
    for (const annualReturn of [-99.99, -8, 0, 0.1, 12, 30]) {
        let balance = 0;
        for (let month = 0; month < 36; month++) {
            balance = balance * (1 + annualReturn / 1200) + 7500.50;
        }
        closeTo(calculate({ amount: 7500.50, annualReturn, years: 3 }).futureValue, balance);
    }
});

test("lump sum agrees with a simple single-year example", () => {
    assert.deepEqual(calculate({ type: "lump-sum", amount: 1000, annualReturn: 10, years: 1 }), {
        futureValue: 1100, totalInvested: 1000, estimatedGains: 100
    });
});

for (const [field, values] of Object.entries({
    type: ["weekly", "", null],
    amount: [0, -1, NaN, Infinity, "5000", null],
    annualReturn: [-100, -101, NaN, Infinity, "12", null],
    years: [0, -1, 1.5, NaN, Infinity, "10", Number.MAX_SAFE_INTEGER]
})) {
    for (const value of values) {
        test(`rejects invalid ${field}: ${String(value)}`, () => {
            assert.throws(() => calculate({ [field]: value }), error =>
                error instanceof InvestmentInputError && error.field === field && error.message.length > 0);
        });
    }
}

test("rejects numeric overflow instead of showing infinite or unsafe currency values", () => {
    for (const overrides of [
        { years: 10000, annualReturn: 100 },
        { type: "lump-sum", years: 10000, annualReturn: 100 },
        { amount: Number.MAX_SAFE_INTEGER },
        { type: "lump-sum", amount: 1e20, annualReturn: -50 }
    ]) {
        assert.throws(() => calculate(overrides), /numeric range/);
    }
});
