#!/usr/bin/python

import tokenizer
import rule_base
import copy
import sys

# good notes http://prog.vub.ac.be/~cderoove/declarative_programming/decprog3_sld_cut_naf.pdf

class Results:
  def __init__(self):
    self.name_mappings = dict()

class Solver:
  def __init__(self):
    #rule_base = None
    #goals = None
    pass

  def solve(self, test_file_name, test_query):
    #test_file_name = "test_rules"
    #test_query = "brother(X,Y)."
    #test_query = "sibling(X,X)."

    # load rules and goal
    self.rule_base = rule_base.RuleBase()
    rules = self.rule_base.load_rules_from_file(test_file_name)
    goal = self.rule_base.load_goal_from_string(test_query)
    #print "Goal:", goal.pp()

    # init goals
    goals = list()
    mapping = dict()
    if goal.name == "<=":
      goals.append(self._make_uppercase_temp_var(goal.new_goal,mapping))
      rules.append(goal.new_rule)
    else:
      goals.append(self._make_uppercase_temp_var(goal,mapping))
    # init results
    results = Results()
    results.name_order = self.rule_base.get_var_names_from_string(test_query)
    for key in mapping.keys():
      results.name_mappings[key] = mapping[key]
    # solve!
    if not self._recursive_solve(rules, goals, results, len(goals)):
      print "False\n"

  def _make_uppercase_temp_rule(self, rule, mapping=None):
    if mapping is None:
      mapping = dict()
    result_rule = rule_base.Rule()
    result_rule.left_side = self._make_uppercase_temp_var(rule.left_side, mapping)
    for var in rule.right_side:
      if var.name == "<=":
        result_rule.right_side.append(self._make_uppercase_temp_hyp(var, mapping))
      else:
        result_rule.right_side.append(self._make_uppercase_temp_var(var, mapping))
    return result_rule

  def _make_uppercase_temp_hyp(self, hyp, mapping=None):
    if mapping is None:
      mapping = dict()
    result_hyp = rule_base.Hypothetical()
    result_hyp.new_goal = self._make_uppercase_temp_var(hyp.new_goal, mapping)
    result_hyp.new_rule = self._make_uppercase_temp_rule(hyp.new_rule, mapping)
    return result_hyp

  def _make_uppercase_temp_var(self, var, mapping=None):
    if mapping is None:
      mapping = dict()
    if var.is_temp() and var.parent is None:
      # capital names should have no subvars
      # if capital check if in the mapping
      if var.name in mapping.keys():
        result_var = mapping[var.name]
      else:
        # add to the mapping
        result_var = rule_base.TempVar()
        mapping[var.name] = result_var
    elif var.is_temp():
      return var
    else:
      # lowercase keep the same name
      result_var = rule_base.Variable()
      result_var.name = var.name
      # recursively make temp vars of the subvars
      for v in var.subvars:
        result_var.subvars.append(self._make_uppercase_temp_var(v, mapping))
    return result_var


  def _unify(self, goal, rule):
    # only look at topmost parents when _unifying
    while goal.parent is not None:
      goal = goal.parent
    while rule.left_side.parent is not None:
      rule.left_side = rule.left_side.Parent

    # match left side with goal
    if rule.left_side.is_temp():
      rule.left_side.parent = goal
      return True
    elif goal.is_temp():
      goal.parent = rule.left_side
      return True
    elif rule.left_side.name == goal.name and len(rule.left_side.subvars) == len(goal.subvars):
      for a, b in zip(goal.subvars, rule.left_side.subvars):
        if not self._unify_vars(a, b):
          return False
      return True
    else:
      return False

  def _unify_vars(self, goal_var, rule_var):
    # only look at topmost parents when _unifying
    while goal_var.parent is not None:
      goal_var = goal_var.parent
    while rule_var.parent is not None:
      rule_var = rule_var.parent

    # match them
    if goal_var.is_temp() and rule_var.is_temp():
      parent = rule_base.TempVar()
      goal_var.parent = parent
      rule_var.parent = parent
      return True
    elif goal_var.is_temp():
      goal_var.parent = rule_var
      return True
    elif rule_var.is_temp():
      rule_var.parent = goal_var
      return True
    elif rule_var.name == goal_var.name and len(rule_var.subvars) == len(goal_var.subvars):
      for a, b in zip(goal_var.subvars, rule_var.subvars):
        if not self._unify_vars(a, b):
          return False
      return True
    else:
      return False

  def _recursive_solve(self, rules, goals, results, num_orig_rules, recursive_depth_left=100):
    if recursive_depth_left < 0:
      print "recursion depth limit reached!"
      sys.exit(0)

    if not goals:
      # make goals contain the results, so that deepcopy copies the results too.
      # or put them in a list, and deepcopy the list

      num_printed = 0
      for key in results.name_order:
        result_var = results.name_mappings[key]
        while result_var.parent is not None:
          result_var = result_var.parent
        result_str = result_var.pp(True)
        if result_str[0:5] != "_temp":
          print key, "=", result_var.pp(True)
          num_printed += 1

      if num_printed == 0:
        print "True"
      print ""
      return True

    # try matching in order of each var in goals and each rule in rules
    result_found = False

    for i in xrange(len(rules)):

      # need to deepcopy the goals, results, and rules
      # deepcopy results at the same time as goals so that the vars in both have the same references
      (goals_copy, results_copy, rules_copy) = copy.deepcopy((goals, results, rules))

      # get the var we are trying to match
      var = goals_copy[0]
      # need to pass a copy of the rule with temps
      rule = rules_copy[i]
      temp_rule = self._make_uppercase_temp_rule(rule)

      # additional facts can only be used once
      # additional rules can be used more than once

      #print "_unifying:"
      #print "var:", var.pp(True)
      #print "rule:", rule.pp(True)
      #print "temp_rule:", temp_rule.pp(True)
      if self._unify(var, temp_rule):
        #print "_unify was successful\n"
        # update goals
        del(goals_copy[0])
        # remove added facts (keep added rules)
        if i >= num_orig_rules and len(temp_rule.right_side) == 0:
          del(rules_copy[i])

        new_goals = []
        for v in temp_rule.right_side:
          if v.name == "<=":
            #print "appending rule:", v.new_rule.pp(True)
            rules_copy.append(v.new_rule)
            #print "appending goal:", v.new_goal.pp(True)
            new_goals.append(v.new_goal)
          else:
            new_goals.append(v)
        goals_copy = new_goals + goals_copy
        if self._recursive_solve(rules_copy, goals_copy, results_copy, num_orig_rules, \
                                recursive_depth_left-1):
          result_found = True
      else:
        #print "_unify was unsuccessful\n"
        pass

    return result_found


if __name__ == "__main__":
  filename = sys.argv[1]
  query = sys.argv[2]
  s = Solver()
  s.solve(filename, query)