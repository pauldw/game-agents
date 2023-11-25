import java.io.File
import java.text.SimpleDateFormat
import java.util.*
import kotlin.math.sqrt
import kotlin.random.Random

const val YEARS = 8 // Number of years to simulate
const val QUARTERLY_VEST_AMOUNT = 25_000.00 // Value of stock that vests quarterly
const val VEST_AMOUNT_INFLATION = 0.02 // Annual inflation of vest amount
const val WIRE_DELAY = 10 // Number of days a wire transfer is delayed
const val LOAN_INTEREST_RATE = 0.05 // Margin loan annual interest rate (or savings return if self-funded)

const val SIMULATION_COUNT = 1000 // Number of simulations to run
const val LOG_LEVEL = 0 // Set to 1 for more verbose logging

fun main() {
    val noMarginFinalPortfolioValues = runScenario(::NoMarginEngineer, SIMULATION_COUNT)
    val marginFinalPortfolioValues = runScenario(::MarginEngineer, SIMULATION_COUNT)

    println("No Margin: ${noMarginFinalPortfolioValues.average().toCurrency()}")
    println("   Margin: ${marginFinalPortfolioValues.average().toCurrency()}")
    println()
    println("Difference: ${(marginFinalPortfolioValues.average() - noMarginFinalPortfolioValues.average()).toCurrency()} over $YEARS years")
}

data class HistoricalData(val date: Date, val price: Double, val returnFromPreviousDay: Double)

class HistoricalDataSampler(private val random: Random = Random.Default) {
    fun random(): HistoricalData {
        return historicalData.random(random)
    }

    companion object {
        private val historicalData = File("src/main/resources/historical_data.tsv").readLines()
            .drop(1)
            .map { it.split("\t") }
            .map { HistoricalData(it[0].toDate(), it[1].toCurrency(), it[2].toPercentage()) }
    }
}

fun runScenario(engineerConstructor: (StockPlan, BrokerageAccount) -> Engineer, count: Int): List<Double> {
    val finalPortfolioValues = mutableListOf<Double>()
    (1 .. count).forEach {
        val stockPlan = StockPlan(QUARTERLY_VEST_AMOUNT)
        val historicalDataSampler = HistoricalDataSampler(Random(it)) // Use the iterator as the seed so separate scenarios use the same random data
        val brokerageAccount = BrokerageAccount(0.0, historicalDataSampler)
        val engineer = engineerConstructor(stockPlan, brokerageAccount)

        val simulator = Simulator()
        simulator.schedule(stockPlan)
        simulator.schedule(brokerageAccount)
        simulator.schedule(engineer)

        (1..260 * YEARS).forEach { _ ->
            simulator.tick()
        }
        finalPortfolioValues.add(brokerageAccount.getBalance())
    }

    return finalPortfolioValues
}

abstract class Engineer(private val stockPlan: StockPlan, private val brokerageAccount: BrokerageAccount) : Process

interface Process {
    fun tick(simulator: Simulator)
}

interface Instrument {
    fun deposit(amount: Double)
    fun withdraw(maxAmount: Double): Double
    fun getBalance(): Double
}

class Simulator {
    private val processes = mutableListOf<Process>()
    private var age = 0

    fun schedule(process: Process) {
        processes.add(process)
    }

    fun tick() {
        age += 1
        val tickProcesses = processes.toList()
        processes.clear() // Processes will re-schedule themselves if they need to continue running
        tickProcesses.forEach { process ->
            process.tick(this)
        }
    }

    fun log(message: String) {
        if (LOG_LEVEL >= 1) {
            println("$age: $message")
        }
    }
}

class NoMarginEngineer(private val stockPlan: StockPlan, private val brokerageAccount: BrokerageAccount): Engineer(stockPlan, brokerageAccount) {
    override fun tick(simulator: Simulator) {
        val stockPlanBalance = stockPlan.getBalance()
        if(stockPlanBalance > 0.0) {
            val wireTransfer = WireTransfer(stockPlan, brokerageAccount, stockPlanBalance)
            simulator.schedule(wireTransfer)
        }
        simulator.schedule(this) // Keep on keeping on
    }
}

class MarginEngineer(private val stockPlan: StockPlan, private val brokerageAccount: BrokerageAccount): Engineer(stockPlan, brokerageAccount) {
    override fun tick(simulator: Simulator) {
        val stockPlanBalance = stockPlan.getBalance()
        if(stockPlanBalance > 0.0) {
            val wireTransfer = WireTransfer(stockPlan, brokerageAccount, stockPlanBalance) { amount ->
                brokerageAccount.returnLoan(brokerageAccount.getLoanBalance())
            }
            simulator.schedule(wireTransfer)
            brokerageAccount.borrowLoan(stockPlanBalance)
        }
        simulator.schedule(this) // Keep on keeping on
    }
}

class StockPlan(private var quarterlyVestAmount: Double) : Instrument, Process {
    private var age = 0
    private var vested = 0.0

    override fun tick(simulator: Simulator) {
        age += 1
        if(age % 65 == 0) {
            vested += quarterlyVestAmount
        }
        quarterlyVestAmount *= (1.0 + VEST_AMOUNT_INFLATION / 260.0)

        simulator.schedule(this)
    }

    override fun deposit(amount: Double) {
        throw Exception("Cannot deposit into a stock plan")
    }

    override fun withdraw(maxAmount: Double): Double {
        val amount = if(maxAmount > vested) vested else maxAmount
        vested -= amount
        return amount
    }

    override fun getBalance(): Double {
        return vested
    }
}

class BrokerageAccount(private var portfolioValue: Double, private val historicalDataSampler: HistoricalDataSampler) : Instrument, Process {
    private var loanValue = 0.0

    override fun tick(simulator: Simulator) {
        val portfolioReturn = (historicalDataSampler.random().returnFromPreviousDay * portfolioValue)
        portfolioValue += portfolioReturn
        simulator.log("Portfolio return: ${portfolioReturn.toCurrency()}, portfolio value: ${portfolioValue.toCurrency()}")

        val loanInterest = LOAN_INTEREST_RATE/260.0 // TODO have this match historical loan interest rates for that day
        val loanExpense = loanValue * loanInterest
        loanValue += loanExpense
        simulator.log("Loan expense: ${loanExpense.toCurrency()}, loan value: ${loanValue.toCurrency()}, loan interest rate: ${loanInterest.toPercentage()}")

        simulator.schedule(this)
    }

    override fun deposit(amount: Double) {
        portfolioValue += amount
    }

    override fun withdraw(maxAmount: Double): Double {
        throw Exception("Cannot withdraw from a brokerage account")
    }

    override fun getBalance(): Double {
        return portfolioValue - loanValue
    }

    fun borrowLoan(amount: Double) {
        loanValue += amount
        portfolioValue += amount
    }

    fun returnLoan(amount: Double) {
        loanValue -= amount
        portfolioValue -= amount
    }

    fun getLoanBalance(): Double {
        return loanValue
    }
}

class WireTransfer(source: Instrument, private val destination: Instrument, maxAmount: Double, private val depositedCallback: (Double) -> Unit = {}): Process {
    private var balance = 0.0
    private var age = 0

    init {
        balance = source.withdraw(maxAmount)
    }

    override fun tick(simulator: Simulator) {
        age += 1
        if(age >= WIRE_DELAY) {
            simulator.log("Wire deposit ${balance.toCurrency()}")
            destination.deposit(balance)
            depositedCallback(balance)
            return // Stop processing by not re-scheduling ourselves
        }
        simulator.log("Pending wire of ${balance.toCurrency()}")
        simulator.schedule(this)
    }
}

// Format Double to currency string
fun Double.toCurrency(): String {
    return "$" + String.format("%,.2f", this)
}

// Transform date string to date
fun String.toDate(): Date {
    return SimpleDateFormat("yyyy-MM-dd").parse(this)
}

// Transform currency string to double
fun String.toCurrency(): Double {
    return this.replace("$", "").replace(",", "").toDouble()
}

// Transform percentage string to double
fun String.toPercentage(): Double {
    return this.replace("%", "").toDouble() / 100.0
}

// Get average of list of Doubles
fun List<Double>.average(): Double {
    return this.reduce { acc, double -> acc + double } / this.size
}

// Get median of a list of Doubles
fun List<Double>.median(): Double {
    val sorted = this.sorted()
    val middle = sorted.size / 2
    return if(sorted.size % 2 == 0) {
        (sorted[middle] + sorted[middle - 1]) / 2.0
    } else {
        sorted[middle]
    }
}

// Double to percentage string
fun Double.toPercentage(): String {
    return String.format("%.2f", this * 100.0) + "%"
}

// Get standard deviation of a list of Doubles
fun List<Double>.standardDeviation(): Double {
    val average = this.average()
    val variance = this.map { it - average }.map { it * it }.average()
    return sqrt(variance)
}