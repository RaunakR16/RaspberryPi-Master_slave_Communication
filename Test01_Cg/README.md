## Physical connections (wiring)

|  Signal  | Master Pi (GPIO#) | Pin (header) | Slaves share — connect to each Pi’s corresponding pin |
| :------: | :---------------: | :----------: | :---------------------------------------------------- |
| **MOSI** |      GPIO 10      |    Pin 19    | All slaves: MOSI ←→ GPIO 10 (pin 19)                  |
| **MISO** |       GPIO 9      |    Pin 21    | All slaves: MISO ←→ GPIO 9 (pin 21)                   |
| **SCLK** |      GPIO 11      |    Pin 23    | All slaves: SCLK ←→ GPIO 11 (pin 23)                  |
|  **CS₁** |    GPIO 8 (CE0)   |    Pin 24    | Slave ID 1: CS ←→ GPIO 8                              |
|  **CS₂** |    GPIO 7 (CE1)   |    Pin 26    | Slave ID 2: CS ←→ GPIO 7                              |
|  **CS₃** |       GPIO 5      |    Pin 29    | Slave ID 3: CS ←→ GPIO 5                              |
|  **CS₄** |       GPIO 6      |    Pin 31    | Slave ID 4: CS ←→ GPIO 6                              |
|  **CS₅** |      GPIO 13      |    Pin 33    | Slave ID 5: CS ←→ GPIO 13                             |

- All grounds must be common: connect the GND of the master to all slave GNDs.
