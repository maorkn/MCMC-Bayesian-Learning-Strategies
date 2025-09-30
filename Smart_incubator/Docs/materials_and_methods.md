 # Materials and Methods

## Simulation Environment

The simulation models a population of agents evolving in a cyclical environment with five discrete Hidden Environmental States (HES 0–4). Each day consists of a deterministic progression through all five states in sequence: $HES 0 \rightarrow HES 1 \rightarrow HES 2 \rightarrow HES 3 \rightarrow HES 4$, then cycling back to HES 0 on the following day. Each environmental state is characterized by three parameters: normalized temperature (T), carbon concentration (C), and nitrogen concentration (N), as shown in Table 1.

**Table 1: Environmental State Parameters**
| HES | Stage | Temperature (T) | Carbon (C) | Nitrogen (N) | C/N Ratio |
|-----|-------|----------------|------------|--------------|-----------|
| 0   | Dawn  | -0.34          | 0.1        | 1.0          | 0.1       |
| 1   | Morning | 1.38         | 1.0        | 0.1          | 10.0      |
| 2   | Midday  | -0.34        | 0.8        | 0.2          | 4.0       |
| 3   | Afternoon | 0.80       | 0.8        | 0.2          | 4.0       |
| 4   | Dusk    | -1.49        | 0.1        | 1.0          | 0.1       |

At each environmental state transition, agents receive noisy observations of the true environmental parameters, with Gaussian noise ($\sigma = 0.2$) added to each dimension. To test robustness, we implemented an environmental stochasticity parameter ($\epsilon$) that introduces a probability of random state transitions instead of the deterministic sequence.

## Agent Architecture

Both agent types share an identical 452-bit boolean genome structure that encodes three key components:

### Genome Structure
1. **Phenotype Sequence (320 bits)**: Five 64-bit vectors, each encoding one of three possible phenotypes (P1, P2, or P3) using a nearest-centroid decoding scheme
2. **Baseline Transition Probability (100 bits)**: Encodes a probability $p_{\text{base}} \in [0,1]$ calculated as the proportion of '1' bits
3. **Temperature Sensitivity (32 bits)**: Encodes a sensitivity factor $C \in [-1,1]$ normalized around the midpoint

### Phenotype Transition Mechanics
Agent phenotype transitions are governed by a temperature-sensitive probabilistic mechanism. The effective transition probability at each environmental state is calculated as:

$P_{\text{effective}} = p_{\text{base}} \times (1 + C \times \text{norm}(\Delta T_{\text{obs}}))$

where $\Delta T_{\text{obs}}$ is the observed temperature change between consecutive states, and `norm()` normalizes the temperature change to [0,1]. This mechanism allows agents to use temperature cues to time their phenotype transitions appropriately within the daily cycle.

## Fitness Landscape

The fitness landscape implements a complex multi-peak structure with conditional bonuses designed to create valley-crossing challenges. The base fitness matrix assigns different fitness values to each phenotype in each environmental state:

**Base Fitness Matrix**
| HES | P1  | P2  | P3  |
|-----|-----|-----|-----|
| 0   | 1.0 | 0.1 | 0.6 |
| 1   | 0.3 | 0.8 | 0.6 |
| 2   | 0.3 | 0.8 | 0.6 |
| 3   | 0.3 | 0.8 | 1.2 |
| 4   | 1.0 | 0.1 | 0.6 |

### Conditional Fitness Mechanism
A critical feature of the fitness landscape is the preparatory phenotype mechanism. When an agent expresses phenotype P3 in HES 3, it activates a 2-step "preparation countdown" that enables maximum fitness (1.0) for phenotype P1 in subsequent nitrogen-rich states (HES 4 and HES 0). Without this preparation, P1 expression in nitrogen-rich states yields only 30% of its potential fitness (0.3), creating a temporal dependency that requires predictive adaptation.

## Mathematical Model of Fitness Dynamics

### Formal Model for Fitness Gain

We can formalize the fitness dynamics for both agent types as follows:

#### Blind Agent (BA) Fitness Model
For a BA agent i at time t, the fitness is determined solely by its genetically-encoded phenotype sequence:

$V_{\text{BA},i}(t) = \frac{1}{5} \sum_{h=0}^{4} F(G_i(t)[\phi_i(h)], h) - P_{\text{conditional}}(G_i(t), h)$

where:
- $G_i(t)$ is the genetically-determined phenotype sequence at generation t
- $\phi_i(h)$ is the phenotype index used in environmental state h
- $F(p,h)$ is the base fitness lookup function for phenotype p in state h
- $P_{\text{conditional}}$ accounts for the preparatory phenotype penalty (0.7 reduction if P1 used without P3 preparation)

The evolutionary dynamics follow:
$G_i(t+1) = G_i(t) \oplus M(\mu)$

where $M(\mu)$ represents bit-flip mutations with probability $\mu = 10^{-4}$.

#### Memory Bayesian Agent (MBA) Fitness Model
For an MBA agent i at time t, fitness incorporates both learned strategy and plasticity cost:

$V_{\text{MBA},i}(t) = \frac{1}{5} \sum_{h=0}^{4} [F(L_i(t)[\phi_i(h)], h) - C_{\text{plasticity}}(L_i(t), G_i(t))] - P_{\text{conditional}}(L_i(t), h)$

where:
- $L_i(t)$ is the learned phenotype sequence (posterior)
- $G_i(t)$ is the genomic phenotype sequence (prior)
- $C_{\text{plasticity}}$ is the continuous metabolic cost of plasticity

The plasticity cost function is defined as:
$C_{\text{plasticity}}(L_i, G_i) = \lambda_H \sum_{j=1}^{5} I(L_i[j] \neq G_i[j]) + \lambda_{KL} D_{KL}(p_{\text{learned}} \| p_{\text{genomic}})$

where $I()$ is the indicator function, $\lambda_H = 0.01$, and $\lambda_{KL} = 0.02$.

#### Learning Dynamics
The MBA's learned strategy evolves within lifetime according to:

$L_i(t, h+1) = \begin{cases} L_i(t, h) \oplus \text{Random\_phenotype\_switch} & \text{if } R(t,h) > 0.2 \text{ and } U(0,1) < \eta \\ L_i(t, h) & \text{otherwise} \end{cases}$

where $R(t,h) = F_{\text{optimal}}(h) - F_{\text{realized}}(t,h)$ is the regret function and $\eta = 0.3$ is the learning rate.

#### Genetic Assimilation Dynamics
When an MBA achieves sustained success, learned adaptations can be genetically assimilated:

If $\sum_{\tau=t-K+1}^{t} I(V_{\text{MBA},i}(\tau) > \theta) \ge K$, then $G_i(t+1)[j] \leftarrow L_i(t)[j]$

where K = 3 consecutive successful generations and $\theta = 0.65$ is the fitness threshold.

#### Comparative Advantage Model
The relative advantage of MBA over BA can be expressed as:

$\Delta(t) = E[V_{\text{MBA}}(t)] - E[V_{\text{BA}}(t)]$

This advantage is positive when the learning benefit outweighs the plasticity cost:
$E[F(L(t)) - F(G(t))] > E[C_{\text{plasticity}}(L(t), G(t))]$

The model predicts MBA advantage in predictable environments where learning can identify optimal strategies faster than mutation alone, but BA advantage in highly stochastic environments where plasticity costs exceed learning benefits.

## Agent Types

### Blind Agent (BA)
The Blind Agent represents a purely genetic strategy with no learning capability. Its behavior is entirely determined by its decoded genome:
- Phenotype sequence: Fixed at birth from genetic encoding
- Transition timing: Based solely on genetically encoded temperature sensitivity and baseline probability
- No plasticity cost or learning mechanism
- Relies entirely on mutation ($\mu = 10^{-4}$ per bit) and selection for adaptation

### Memory Bayesian Agent (MBA)
The MBA implements a dual-layer architecture enabling within-lifetime learning:

#### Dual-Layer Strategy
- **Genomic Layer (Prior)**: The inherited 452-bit genome representing the evolutionary baseline
- **Learning Layer (Posterior)**: A mutable copy of the phenotype sequence and transition probability that drives actual behavior

#### Plasticity Cost
The MBA pays a continuous metabolic cost for any divergence between its learned strategy and genomic prior:

$C_{\text{plasticity}} = \lambda_H \times \sum(P_{\text{learned},i} \neq P_{\text{geno},i}) + \lambda_{KL} \times D_{KL}(p_{\text{learned}} \| p_{\text{geno}})$

where $\lambda_H = 0.01$ (Hamming distance cost) and $\lambda_{KL} = 0.02$ (KL divergence cost for transition probabilities).

#### Learning Mechanism
The MBA employs a regret-based "trial and error" learning system:

1. **Regret Calculation**: After each environmental state, agents calculate regret as the difference between optimal possible fitness and realized fitness
2. **Learning Trigger**: If regret > 0.2, learning is activated with probability $\eta = 0.3$
3. **Phenotype Update**: Random selection of alternative phenotypes for the current sequence position
4. **Probability Update**: Gradual adjustment of transition probability toward an optimal target ($p_{\text{target}} = 0.9$)

#### Genetic Assimilation
Successful learned strategies can be permanently encoded into the genome through genetic assimilation. When an agent achieves high fitness (>0.65) for 3 consecutive days in a given sequence position, the learned phenotype for that position is written back to the genome, reducing future plasticity costs and making the adaptation heritable.

## Population Dynamics

Evolution proceeds via a Moran process maintaining constant population size:

1. **Parent Selection**: Agents are selected for reproduction with probability proportional to their daily fitness
2. **Victim Selection**: A random agent is chosen for replacement
3. **Offspring Production**: The parent produces a clonal offspring subject to mutation
4. **Mutation**: Each genome bit flips with probability $\mu = 10^{-4}$ (identical for both BA and MBA agent types)

## Experimental Protocols

### Core Evolution Experiments
Independent populations of 100 BA-only, 100 MBA-only, and mixed populations (50 BA + 50 MBA) were evolved for 500 days across 30 independent replicates. Daily fitness, population entropy, and plasticity costs were recorded.

### Stochasticity Stress Test
Mixed populations (50 BA + 50 MBA) were evolved under varying environmental noise levels ($\epsilon$ = 0.0 to 1.0 in increments of 0.05) for 200 days across 10 replicates per noise level to identify the predictability threshold where plasticity becomes maladaptive.

### Genetic Lock-in Test
Populations were evolved in the standard environment for 300 days, then subjected to a permanent environmental shift (reversed HES sequence order) to test adaptive flexibility. Recovery dynamics were monitored for an additional 200 days.

### Long-term Competition
Mixed populations (500 BA + 500 MBA) were co-evolved for 100,000 days to assess long-term evolutionary stability and the emergence of evolutionary rescue effects.

## Data Collection and Analysis

### Fitness Tracking
Daily fitness was calculated as the mean fitness across all five environmental states within each day. Final daily fitness for MBAs included subtraction of plasticity costs.

### Population Entropy
Shannon entropy was calculated from the distribution of phenotype sequences within each population: $H = -\sum(p_i \times \log_2(p_i))$, where $p_i$ is the frequency of sequence i.

### Muller Plots
Population genetic dynamics were visualized using Muller plots showing the frequency trajectories of the 9 most common genotype sequences over time, with remaining sequences aggregated as "Other."

### Statistical Analysis
All experiments used multiple independent replicates with results reported as mean ± standard error of the mean (SEM). Population-level dynamics were averaged across replicates, and evolutionary trajectories were analyzed using time-series methods.

## Implementation Details

The simulation was implemented in Python using NumPy for numerical computations and SciPy for statistical functions. The complete codebase is structured as a modular package with separate components for:
- Agent classes (`mba_vs_ba_sim.agents`)
- Environmental dynamics (`mba_vs_ba_sim.env`)
- Population evolution (`mba_vs_ba_sim.population`)
- Experimental scripts (`scripts/`)

All random number generation used NumPy's PCG64 generator with explicit seed management for reproducibility. Computational experiments were designed to be fully deterministic given input parameters and random seeds.

## Smart Incubator Platform

The Smart Incubator is an automated experimental platform designed to subject cell cultures to complex, long-term environmental protocols. It provides precise control over temperature and allows for the timed delivery of physical stimuli (light and vibration). The system is built on a modular MicroPython framework, enabling robust, unattended operation for studying phenotypic plasticity, learning, and memory in microorganisms like *Capsaspora owczarzaki*.

### Hardware and System Architecture

The platform is built around an ESP32 microcontroller, which orchestrates all subsystems. The hardware components and their corresponding GPIO pin assignments are detailed in Table 2.

**Table 2: Smart Incubator Hardware Components and Pinout**
| Component                  | Interface | Pin(s) & Function                             |
|----------------------------|-----------|-----------------------------------------------|
| **Control Unit**           | -         | ESP32-WROOM-32 (240MHz)                       |
| **Temperature Sensing**    | SPI       | MAX31865 with PT100 RTD                        |
|                            |           | SCK: 14, MOSI: 13, MISO: 12, CS: 5            |
| **Thermal Actuators**      | PWM       | PTC Heater (Heating, Pin 33)                  |
|                            |           | TEC1 Peltier (Cooling, Pin 27)                |
| **Conditional Stimuli**    | PWM       | LED Module (Light, Pin 25)                    |
|                            |           | Vibration Motor (Vibration, Pin 16)           |
| **Data Storage**           | SPI       | MicroSD Card Module                           |
|                            |           | SCK: 14, MOSI: 13, MISO: 12, CS: 15            |
| **User Interface**         | I2C       | SSD1306 128x64 OLED Display                   |
|                            |           | SCL: 22, SDA: 21                              |

The software architecture is multi-layered, separating high-level experimental logic from hardware drivers to ensure modularity and resilience. This includes automated initialization with retry logic, comprehensive error handling, and memory management via periodic garbage collection.

### Thermal and Stimulus Control System

#### Thermal Regulation
Precise temperature control is achieved through a Proportional-Integral-Derivative (PID) controller that manages the PTC heater and TEC1 cooler. The PID parameters are tuned for the system's thermal properties (kp=6.0, ki=0.02, kd=1.5) and feature an anti-windup mechanism to prevent integral term overshoot. The controller operates within a deadband of -0.1°C to +0.5°C to minimize actuator oscillation.

To ensure measurement accuracy, the system employs an advanced noise-filtering protocol for the MAX31865 sensor. Each temperature reading is the median of 5 rapid samples, and a change-rate limiter discards spurious readings that deviate more than 5°C from the previous measurement. This results in highly stable thermal control, maintaining a basal temperature of 23°C with an accuracy of +0.45°C to +0.65°C and a heat shock temperature of 32°C with an accuracy of -0.52°C to -2.52°C, depending on the experimental protocol.

#### Stimulus Delivery
The system can deliver two types of unconditional stimuli (US): optical (LED) and mechanical (vibration). The intensity of each stimulus is independently configurable via PWM (0–100%). The vibration motor operates on a default pulsed interval of 20 seconds on and 60 seconds off to prevent motor overheating and reduce mechanical stress on the culture.

### Experimental Protocols

The incubator executes experiments in automated, unattended cycles. Each cycle's duration is randomized within a configurable range (default: 200–400 minutes) to prevent organismal entrainment to a fixed cycle length. A typical cycle consists of a prolonged basal temperature phase (default: 23°C) followed by a shorter heat shock phase (default: 32°C).

A key experimental parameter is the `correlation` mode, which defines the temporal relationship between the unconditional stimulus (US) and the heat shock (HS):
- **Non-Temporal (Mode 0):** The timing of both US and HS are randomized independently within the cycle. This creates a control condition with no predictive relationship between the cue and the stressor, resulting in a highly variable stimulus-stress delta (-58.1 ± 113.9 min).
- **Temporal (Mode 1):** The US is programmed to precede the HS by a precise, fixed interval (default: 30 minutes). This mode is used to test for predictive learning and enables highly precise cue-stress pairing, achieving a stimulus-stress delta of 30.0 ± 0.3 min.

### Data Acquisition and Integrity

The system logs a complete data snapshot every 10 seconds to a FAT32-formatted SD card. For each experimental run, a unique directory is created with the format `data/DDMMYYYY_correlation/`. The logged data includes:
- **`meta.json`**: A file containing all initial parameters for the experiment.
- **`cycle_[N]_TIMESTAMP.json`**: Individual JSON files for each 10-second snapshot, containing timestamp, current temperature, setpoint, PID output, power levels, and stimulus status.
- **`cycle_[N]_summary.json`**: A summary file generated at the end of each cycle with statistics such as min/max/average temperatures, duration, and error counts.
- **`manifest.json`**: A file that ensures data integrity by storing SHA-256 checksums for all data files written during the experiment. The system verifies these checksums to detect any file corruption.
