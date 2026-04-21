
Feature: fully_populated_complex_update

  Scenario: No description found
    Given a resource of type "tfcoremock_complex_resource" named "complex"
    And the resource has the following attributes:
      | id | "64564E36-BFCB-458B-9405-EBBF6A3CAC7A" |
      | number | 987654321.0 |
      | integer | 123456789 |
      | float | 123456789.0 |
      | string | "a not very long or complex string" |
      | bool | true |
      | list | [{"string": "this is my first entry in the list, and doesn't contain anything interesting"}, {"string": "this is my second entry in the list\nI am a bit more interesting\nand contain multiple lines\nbut I've been edited"}, {"string": "this is my third entry, and I actually have a nested list", "list": [{"number": 0}, {"number": 1}, {"number": 3}, {"number": 4}]}, {"string": "this is my fourth entry, and I actually have a nested set and I edited my test", "set": [{"number": 0}, {"number": 2}]}] |
      | object | {"string": "i am a nested object", "number": 0, "object": {"string": "i am a nested nested object", "bool": true}} |
      | map | {"key_one": {"string": "this is my first entry in the map, and doesn't contain anything interesting"}, "key_two": {"string": "this is my second entry in the map\nI am a bit more interesting\nand contain multiple lines"}, "key_three": {"string": "this is my third entry, and I actually have a nested list", "list": [{"number": 0}, {"number": 3}, {"number": 1}, {"number": 2}]}, "key_four": {"string": "this is my fourth entry, and I actually have a nested set", "set": [{"number": 0}, {"number": 1}, {"number": 3}, {"number": 4}]}} |
      | set | [{"string": "this is my first entry in the set, and doesn't contain anything interesting"}, {"string": "this is my second entry in the set\nI am a bit more interesting\nand contain multiple lines"}, {"string": "this is my third entry, and I actually have a nested list", "list": [{"number": 0}, {"number": 1}, {"number": 2}]}, {"string": "this is my fourth entry, and I actually have a nested set", "set": [{"number": 0}, {"number": 1}]}] |
      | list_block | [{"string": "{\"index\":0}"}, {"string": "{\"index\":1}", "list": [{"number": 0}, {"number": 1}, {"number": 2}]}] |
      | set_block | [{"string": "{\"index\":1}", "list": [{"number": 0}, {"number": 1}, {"number": 2}]}, {"string": "{\"index\":2}", "set": [{"number": 0}, {"number": 1}]}, {"string": "{\"index\":3}"}] |
    When the resource is created
    Then the resource should exist in the state
    And its attributes in the state should match the provided values
