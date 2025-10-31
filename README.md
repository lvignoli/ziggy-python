# ziggy-python

Python support for the [Ziggy](https://ziggy-lang.io/) data serialization language.
Ziggy schema is not supported.


## Feature list

#### Parsing
- [x] null
- [x] bool
- [x] integers and float in base 10
- [ ] integers and float in base 2, 8 and 16, with scientific notation
- [x] quoted and multiline bytes literals
- [x] tagged literals
- [ ] tagged literals with custom parser
- [x] arrays
- [x] maps
- [x] structs
- [x] structs to custom dataclass
- [ ] root struct


#### Serialization
- [x] None
- [x] bool
- [x] int, float
- [ ] ints and floats in base 2, 8, 16, with scientific notation
- [ ] numpy number types
- [x] str, bytes, byterarray
- [x] Sequence
- [x] Mapping
- [x] enum
- [x] dataclass
- [ ] objects satisfying ZiggySerialize protocol
- [ ] minified ziggy documents
- [ ] tagged literal
