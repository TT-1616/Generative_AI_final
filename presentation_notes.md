# Lightning Presentation Notes

## 1. Context, User, And Problem

My project is NextStop AI, a highway stop planner for Michigan drivers. The user is a long-distance driver, rideshare driver, delivery driver, or small fleet dispatcher trying to decide where to stop next on I-75, I-94, or I-96.

The problem is that the closest stop is not always the best stop. A nearby rest area may have a restroom but no gas, coffee, EV charger, food, or reliable 24-hour status. In the moment, drivers need a clear tradeoff, not a long list of map pins.

## 2. Solution And Design

I built a Streamlit app. The user enters highway, direction, current mile marker, fuel or battery range, must-have amenities, and a natural language request.

The app compares three ideas: a nearest-stop baseline, a deterministic planner, and optional GenAI explanation mode. The deterministic planner calculates distance and filters for needs. The GenAI prompt takes the top candidates and writes a concise recommendation and caution in plain language.

The scope is intentionally narrow: Michigan highway stops, not full navigation.

## 3. Evaluation And Results

I created 8 realistic Michigan scenarios, such as "need gas and coffee," "EV is low," "box truck at night," and "avoid seasonal closed places." The rubric checks whether the top recommended stop matches the expected stop.

The baseline picks the closest stop ahead. It fails when the closest stop lacks the needed amenity. The NextStop planner does better because it accounts for fuel range, direction, amenities, and safety tradeoffs.

The main limitation is data freshness. This app should not replace live navigation or MDOT updates.

## 4. Artifact Snapshot

Show the Streamlit app with this input:

```text
Highway: I-94 eastbound
Current mile marker: 0
Fuel range: 50 miles
Request: I just crossed into Michigan. Need gas and coffee soon.
```

Then show the output:

- Recommended stop: Kalamazoo Fuel Exit
- Distance: 40 miles
- Why: New Buffalo Welcome Center is closer, but it does not have gas or coffee
- Caution: verify live hours, closures, and traffic before driving

Close by saying: NextStop AI does not replace maps. It improves the small decision of choosing the next stop when needs are specific and time matters.
