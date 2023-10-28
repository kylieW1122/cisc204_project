
from bauhaus import Encoding, proposition, constraint, Or, And
from bauhaus.utils import count_solutions, likelihood
from itertools import product, combinations
import random
# These two lines make sure a faster SAT solver is used.
from nnf import config
config.sat_backend = "kissat"

#----------------Constants-----------------
RANKS = (1,2,3,4,5,6,7,8,9) # tuple: ordered and unchangable data structure
SUITS = ('A', 'B', 'C', 'D')
NUM_OF_CARDS = 10
#-------------Global Variables-------------
deck = []
discard = []
player_cards = []

# Encoding that will store all of your constraints
E = Encoding()

class Hashable: #recommanded
    def __hash__(self):
        return hash(str(self))

    def __eq__(self, __value: object) -> bool:
        return hash(self) == hash(__value)

    def __repr__(self):
        return str(self)
 # To create propositions, create classes for them first, annotated with "@proposition" and the Encoding   
@proposition(E)
class Player(Hashable):
    def __init__(self, rank, suit):
        self.a = rank
        self.b = suit

    def __str__(self):
        return f"P({self.a}{self.b})"
    
@proposition(E)
class Opponent(Hashable):
    def __init__(self, rank, suit):
        self.a = rank
        self.b = suit

    def __str__(self):
        return f"O({self.a}{self.b})"
    
@proposition(E)
class Pl_run(Hashable):
    def __init__(self, related_cards):
        self.related_run_cards = related_cards

    def __str__(self):
        return f"player_run_[{self.related_run_cards}]"

@proposition(E)
class Pl_set(Hashable):
    def __init__(self, rank, suit):
        self.rank = rank
        self.excluded_suit = suit

    def __str__(self):
        return f"player_set_{self.rank}_{self.excluded_suit}"
    
@proposition(E)
class Want(Hashable):
    def __init__(self, rank, suit):
        self.a = rank
        self.b = suit

    def __str__(self):
        return f"player_want_{self.a}{self.b}"

@proposition(E)
class Opp_pick(Hashable):
    def __init__(self, rank, suit):
        self.a = rank
        self.b = suit
    
    def __str__(self):
        return f"opp_pick_{self.a}{self.b}"

# Helper functions:
def cardlist_to_dict(my_cardlist):
    '''Takes in a list my_cardlist, returns the dictionary that maps every rank in the list into a set of suits'''
    my_dict = {} # dictionary that maps the ranks into a set of suits, eg. {1:{'A', 'B'}, 3:{'C','A'}}
    for x in my_cardlist:
        if x[0] in my_dict:
            my_dict[x[0]].add(x[1])
        else:
            my_dict[x[0]] = {x[1]}
    return my_dict

def list_of_int_to_list_of_opp_cards(my_rank_list, suit): 
    '''Takes in a list my_int_list and char suit, returns the list of opponent card objects'''
    opp_c_list = []
    for x in my_rank_list:
        opp_c_list.append(Opponent(x, suit))
    return opp_c_list

def initial_game():
    # reset the two global variable and create a shuffled deck
    global deck
    global discard
    discard = []
    deck = list (product (RANKS, SUITS))
    random.shuffle(deck)
    # distribute cards to the player and opponent
    player_cards = deck[:NUM_OF_CARDS]
    # opponent = Player('Opponent', deck[NUM_OF_CARDS:NUM_OF_CARDS*2])
    # deck = deck[NUM_OF_CARDS*2:]
    # print("deck:", deck)
    # print(player_cards)
    # print(opponent)
    return player_cards



# Different classes for propositions are useful because this allows for more dynamic constraint creation
# for propositions within that class. For example, you can enforce that "at least one" of the propositions
# that are instances of this class must be true by using a @constraint decorator.
# other options include: at most one, exactly one, at most k, and implies all.
# For a complete module reference, see https://bauhaus.readthedocs.io/en/latest/bauhaus.html


# Build an example full theory for your setting and return it.
#
#  There should be at least 10 variables, and a sufficiently large formula to describe it (>50 operators).
#  This restriction is fairly minimal, and if there is any concern, reach out to the teaching staff to clarify
#  what the expectations are.
def example_theory():
    # INITIALIZE VARIABLES for the game
    player_cards = initial_game()
    opp_pick_card = deck[NUM_OF_CARDS*2]
    opp_discard_card = None # FIXME: randomize opponent discard card? or make if-statment to determine according to opp's cards

    # Add custom constraints by creating formulas with the variables you created. 
    #-------------------------------------------------------------------------------------------------------
    # CONSTRAINT: If player has card(a,b), then Opponent does not have card(a,b)
    #-------------------------------------------------------------------------------------------------------
    for card in player_cards:
        E.add_constraint(Player(card[0], card[1]) >> ~Opponent(card[0], card[1]))
    #-------------------------------------------------------------------------------------------------------
    # CONSTRAINT: check in player_cards for SETS
    #-------------------------------------------------------------------------------------------------------
    pl_cards_dict = cardlist_to_dict(sorted(player_cards)) # pl_card_dict = {1:{'A','B'}, ....}
    print('player cards: ', pl_cards_dict)
    for el_set in pl_cards_dict.items():
        if (len(el_set[1])>2):
            excl_suit_list = list(set(SUITS).difference(el_set[1]))
            excl_suit = 'Z'
            if len(excl_suit_list)>0:
                excl_suit = excl_suit_list[0]
            # print("there exist a set", el_set, "with exclude: ", excl_suit)
            E.add_constraint(Pl_set(el_set[0], excl_suit))

    #-------------------------------------------------------------------------------------------------------
    # CONSTRAINT: check in player_cards for RUNS
    #-------------------------------------------------------------------------------------------------------
    # BUG: data access error, note that pl_card_dict has key = rank, value = set of the suits
    # is_consecutive = all(pl_cards_dict[i] == pl_cards_dict[i-1] + 1 for i in range(1, len(pl_cards_dict)))  
    # print(is_consecutive)

    #-------------------------------------------------------------------------------------------------------
    # CONSTRAINT: If opponent picks a card of “a” rank and “b” suit, then opponent has that card:
    #-------------------------------------------------------------------------------------------------------
    if opp_pick_card == None:
        E.add_constraint(~Opponent(opp_pick_card[0], opp_pick_card[1]))
    else:
        E.add_constraint(Opponent(opp_pick_card[0], opp_pick_card[1]))

    #-------------------------------------------------------------------------------------------------------
    # CONSTRAINT: If the opponent picks a card of “a” rank and “b” suit, that card must create a meld or contribute to an existing meld.
    #-------------------------------------------------------------------------------------------------------
    # TODO: make it into a if-statement, what if opp didn't pick up the card?
    predecessors = [] # 2D array list of conjunctions - all possible combination of meld 
    # list of all possible SETS with opp_pick_card:
    excl_suit_list = tuple(set(SUITS).difference(opp_pick_card[1]))
    combination_list = list(combinations(excl_suit_list, 2))
    combination_list.append(excl_suit_list) # add possible set of 4 with opp_pick_card
    # print('all combination of sets with card', opp_pick_card,':', combination_list)
    for comb in combination_list:
        temp_list = []
        for each_suit in comb:
            temp_list.append(Opponent(opp_pick_card[0], each_suit))
        predecessors.append(And(temp_list))
    # list of all possible RUNS with opp_pick_card:
    temp_list = [opp_pick_card[0]]
    for upper_r in range(opp_pick_card[0]+1, RANKS[-1]+1):
        temp_list.append(upper_r)
        predecessors.append(And(list_of_int_to_list_of_opp_cards(temp_list, opp_pick_card[1]))) # a copy of the current list with opp card objects
    temp_list = [opp_pick_card[0]]
    for lower_r in reversed(range(RANKS[0], opp_pick_card[0])):
        temp_list.insert(0, lower_r)
        predecessors.append(And(list_of_int_to_list_of_opp_cards(temp_list, opp_pick_card[1]))) # a copy of the current list with opp card objects
    E.add_constraint(Opp_pick(opp_pick_card[0], opp_pick_card[1])>> Or(predecessors)) # FIXME: Find a way to print it out and verify the AND and OR is correct
   
    #-------------------------------------------------------------------------------------------------------
    # CONSTRAINT: If the opponent discards a card of “a” rank and “b” suit, the opponent does not have any meld related to that card. 
    #-------------------------------------------------------------------------------------------------------
    # FIXME: Observation: opp_pick and opp_discard have similar structure of antecedent and consequent, is there a way to simplify it??

    #-------------------------------------------------------------------------------------------------------
    # CONSTRAINT: 
    #-------------------------------------------------------------------------------------------------------

    # You can also add more customized "fancy" constraints. Use case: you don't want to enforce "exactly one"
    # for every instance of BasicPropositions, but you want to enforce it for a, b, and c.:
    # constraint.add_exactly_one(E, a, b, c)

    return E


if __name__ == "__main__":
    T = example_theory()
    # Don't compile until you're finished adding all your constraints!
    T = T.compile()
    # After compilation (and only after), you can check some of the properties
    # of your model:
    print("\nSatisfiable: %s" % T.satisfiable())
    print("# Solutions: %d" % count_solutions(T))
    print("   Solution: %s" % T.solve())

    # print("\nVariable likelihoods:")
    # for v,vn in zip([a,b,c,x,y,z], 'abcxyz'):
    #     # Ensure that you only send these functions NNF formulas
    #     # Literals are compiled to NNF here
    #     print(" %s: %.2f" % (vn, likelihood(T, v)))
    print()
