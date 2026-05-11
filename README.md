# NextStop AI

NextStop AI is a small GenAI app for one narrow business workflow: helping Michigan long-distance drivers choose the next useful highway stop from a route segment.

## Context, User, And Problem

The user is a road trip driver, rideshare driver, delivery driver, or small fleet dispatcher traveling on Michigan highways. Their workflow is simple but stressful: decide whether the next stop is good enough, or whether it is worth driving farther for gas, restroom, coffee, EV charging, truck parking, pet area, or a safer 24-hour stop.

This matters because normal navigation apps can show nearby places, but they do not always explain the tradeoff in plain language. A driver might see that the closest rest area is 6 miles away, but miss that it has no gas, no coffee, or a seasonal closure risk.

Michigan is a good focus because MDOT has public rest-area and welcome-center information. MDOT says rest areas provide modern restrooms and are generally spaced within about an hour of travel, and MDOT also maintains Welcome Centers for traveler information. This prototype uses a small synthetic Michigan stop dataset grounded in those public descriptions, plus synthetic commercial exits for fuel, food, coffee, EV charging, and truck parking.

Sources:

- [MDOT Rest Areas](https://www.michigan.gov/RestAreas)
- [MDOT Tourists: Rest Areas and Welcome Centers](https://www.michigan.gov/mdot/travel/tourists)
- [MDOT Welcome Centers](https://www.michigan.gov/mdot/travel/tourists/welcome-centers)

## Solution And Design

I built a Streamlit app where the user enters:

- highway: I-75, I-94, or I-96
- direction
- current mile marker
- remaining fuel or battery range
- must-have amenities
- natural language request

The app returns:

- recommended next stop
- distance in miles
- risk level
- top candidate table
- plain-language driving plan
- caution reminding the user to verify live conditions

The design has three layers:

- **Nearest-stop baseline:** choose the closest stop ahead, ignoring nuanced needs.
- **Deterministic NextStop planner:** parse needs like gas, restroom, EV charging, pet area, truck parking, and open-24h preference, then score candidate stops by distance, amenities, and fuel risk.
- **GenAI explanation mode:** if `OPENAI_API_KEY` is available, the app sends the driver context and top candidates to OpenAI using `prompts/nextstop_prompt.md`. The model produces a concise explanation and driving plan in JSON.

GenAI is useful because driver requests are messy: "kids need a bathroom," "I can stretch maybe 30 miles," "avoid seasonal closed places," or "I am in a box truck at night." The deterministic layer handles safety constraints, while the LLM makes the recommendation easier to understand.

## Evaluation And Results

The evaluation uses 8 realistic Michigan driving scenarios in `data/evaluation_cases.csv`. A good output means the top recommended stop matches the expected stop for the scenario.

The baseline is intentionally simple: it picks the nearest stop ahead. This is a fair comparison because it resembles the naive workflow of "just stop at the next thing on the map."

Run the evaluation:

```bash
python -m src.evaluate
```

The comparison reports:

- nearest-stop baseline accuracy
- NextStop planner accuracy
- optional LLM explanation-mode accuracy with `--llm`

Expected result for the included deterministic test set:

```text
nearest-stop baseline: lower because it ignores amenities
NextStop planner: higher because it checks fuel range and must-have needs
```

Where it works:

- choosing gas over a closer rest area when fuel is low
- choosing EV charging instead of a normal rest area
- avoiding seasonal or not-24h stops when the user asks for safer options
- explaining tradeoffs between closest and best

Where it fails:

- the dataset is not live
- it does not know traffic, closures, weather, construction, or actual business hours
- it should not replace Google Maps, Apple Maps, Waze, or official MDOT live road information

A human should stay involved when the route affects safety, commercial trucking compliance, winter weather, low fuel emergencies, or accessibility needs.

## Artifact Snapshot

Example input:

```text
Highway: I-94
Direction: eastbound
Current mile marker: 0
Fuel range: 50 miles
Request: I just crossed into Michigan. Need gas and coffee soon.
```

Example output:

```text
Recommended stop: Kalamazoo Fuel Exit
Distance: 40.0 mi
Risk: good match

Plan: Recommended next stop: Kalamazoo Fuel Exit, about 40.0 miles ahead.
Backup option: Battle Creek Family Plaza at 75.0 miles.

Caution: Check live navigation before driving because hours, closures, and services can change.
```

## Setup

Install dependencies:

```bash
pip install -r requirements.txt
```

To use GenAI explanation mode, provide an OpenAI API key. Do not commit the key.

```bash
export OPENAI_API_KEY="your-key-here"
```

You can also create a local `.env` file:

```text
OPENAI_API_KEY=your-key-here
```

## Usage

Run the app:

```bash
streamlit run app.py
```

Then open the local Streamlit URL, enter a driver scenario, and click **Plan next stop**. Without an API key, the app still works using the deterministic planner.

Run the evaluation:

```bash
python -m src.evaluate
```

Run optional LLM evaluation:

```bash
python -m src.evaluate --llm
```

## Project Files

- `app.py`: Streamlit app
- `data/highway_stops.csv`: Michigan-focused synthetic stop dataset
- `data/evaluation_cases.csv`: evaluation scenarios
- `prompts/nextstop_prompt.md`: GenAI prompt
- `src/baseline.py`: baseline and deterministic planner
- `src/llm.py`: OpenAI explanation workflow
- `src/evaluate.py`: evaluation script
- `presentation_notes.md`: 2-3 minute lightning presentation outline

## Data Note

This project does not claim that every stop in the CSV is a real operating facility. Some names are official-style examples, and some are synthetic commercial exits. The goal is to evaluate the workflow design, not to provide live navigation data. A production version should connect to MDOT, mapping, fuel, EV charging, and business-hours data.
