# Case 1: Just the new loads have been passed
- Pass just the new loads to the agent
- Explicitely mentioned that previous loads have not been provided.
- There is no limit/ultimate definition of the loads.
- Input loads units are N, Nmm

## Inputs
USER_PROMPT_1


## Criteria to evaluate the loads processing step

### Loads read correctly

- The agent has called the correct tool (read loads)
- The inputs have been passed correctly

### No comparison loads

- The agent does not call for the comparison loads tool

### Loads have been processed correctly

- The agent does not convert the loads to any other unit, as they already are in the correct units (N, Nmm)
- The agent factors the loads by 1.5 because they have not been specified to be Ultimate loads.
- Load cases are enveloped as per the method definition.
- Load cases are correctly downselected
  - The number of loadcases is correct
  - The ID of the loadcases is correct

### Final value check
- Number of loads files is correct at the provided location.
- The final value of the loads for a given loadcase point and component is correct (perform check on 3 combination of different: loadcases, points and components).


## Case 2:
Same as Case 1, but key differences: 
- old loads provided.
- The loads are in (klbs, lb-ft) units.

### Inputs
USER_PROMPT_2

### Criteria to evaluate the loads processing step
- The loads are converted to the correct units
- The agent compares the loads to the previous ones.
- The results of the comparison loads is correct. (Check overall response and values at 3 different loadcase points and components)


<!-- Unclear if Scenario 3 will be implemented -->
## Case 3: Previous loads are greater than new loads



## Criteria:
- The agent recommendation is not to use the new loads
