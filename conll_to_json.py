#!/usr/bin/env python
# -*- coding: utf-8 -*-

# import pandas as pd
# from pandas import DataFrame
# from nltk.corpus.reader import ConllCorpusReader
# from conllu.parser import parse, parse_tree
# from json import JSONEncoder
import conll_reader.conll_reader_utils as cru
from conll_reader.conll_reader_utils import CONLL_sentence_obj as cso
import re
import json
import codecs


INPUT_CONLL = "work/ud.conll"
# INPUT_CONLL = "query_result.conllu"
INPUT_CONLL_TAB = "work/ud_tab.conll"
OUTPUT_PAS = "work/pas_from_parser.json"


def read_conll_sent_ids(INPUT_CONLL):
    ''' open and read .CONLL file as list of OrderedDict;
    get list of sentences_ids
    '''
    # conll_file = pd.read_csv(INPUT_CONLL, sep='\t')
    file = codecs.open(INPUT_CONLL, 'r', encoding='utf-8')
    conll_file = file.read()
    file.close()

    sent_id = re.findall(r'sent_id = \d+', conll_file)

    return sent_id


def read_conll_with_cru(INPUT_CONLL):
    ''' read .CONLL file into CONLL_token_obj
    with conll_reader_utils by mamsler;
    with changing spaces into tabs
    '''
    with open(INPUT_CONLL, 'r', encoding='utf-8') as file:
        data = file.read()
        # changing spaces into tabs
        data = re.sub(r" +", r"\t", data)
        with open(INPUT_CONLL_TAB, 'w', encoding='utf-8') as outfile:
            outfile.write(data)
    # reading in
    sentences = cru.read_conll_from_file(INPUT_CONLL_TAB)

    return sentences


def build_json_tree(sent, level=None):
    ''' builds json tree with recusion
    '''
    if level is None:
        level = cso.get_root(sent)[0]

    children = cso.get_children(sent, level)

    if len(children) > 0:
            data = {
                level.dep_label: level.lemma,
                "children": [
                    build_json_tree(sent, level=child)
                    for child in children
                ]
            }
    else:
        data = {
            level.dep_label: level.lemma
        }

    return data


def turn_conll_to_json(INPUT_CONLL):
    ''' turn conll_sentece_obj to .json
    take all nodes in a tree and put them into the nested json
    '''
    sentences = read_conll_with_cru(INPUT_CONLL)
    sent_id = read_conll_sent_ids(INPUT_CONLL)
    list_of_sent = []
    for sid, sent in zip(sent_id, sentences):

        _json_tree = build_json_tree(sent)

        neg, passive = detect_neg_passive(sent)
        _json_tree["neg"] = neg
        _json_tree["passive"] = passive

        json_tree = {
            "sent_id": int(sid.split(" = ")[-1]),
            "PAS": _json_tree
        }
        list_of_sent.append(json_tree)
        json_output = json.dumps(list_of_sent, ensure_ascii=False)

    return list_of_sent


def build_full_PAS(INPUT_CONLL):
    '''read input and compilate final PAS of the sentences
    '''
    sentences = read_conll_with_cru(INPUT_CONLL)
    sent_id = read_conll_sent_ids(INPUT_CONLL)
    list_of_sent = []
    if sent_id == []:
        sent_id = ["sent_id = 0"]
    for sid, sent in zip(sent_id, sentences):
        root = cso.get_root(sent)[0]
        PAS = get_PAS(sent, root)

        # add sentence ID
        sentence = {
            "sent_id": int(sid.split(" = ")[-1]),
            "PAS": PAS
        }

        list_of_sent.append(sentence)
        # list_of_sent.append(PAS)

    write_results_into_outfile(list_of_sent)

    return list_of_sent


def get_PAS(sent, start_point):
    '''define PAS of input .conll sentences from the root.
    Takes as arguments: 1) a sentence in .CONLL format;
    2) root or “sub_root” of the pas
    '''
    PAS = {}
    # sub_inf = {}
    root = start_point
    PAS["verb"] = root.lemma

    children = cso.get_children(sent, root)

    for child in children:
        if child.dep_label == "nsubj":
            PAS["subj"] = child.lemma
            sub_pas = get_sub_pas(sent, child)
            # print(sub_pas)
            if sub_pas == {} and sub_pas == []:
                pass
            elif isinstance(sub_pas, list) and sub_pas != []:
                for i, sub in enumerate(sub_pas, 1):
                    if sub.get("subj") is None:
                        sub["subj"] = PAS["subj"]
                        PAS["objc(obj){}".format(i)] = sub
                    else:
                        PAS["objc(obj){}".format(i)] = sub
        # if child.dep_label == "amod":

        if child.dep_label == "nsubj:pass" and PAS.get("subj") is None:
            PAS["subj"] = child.lemma
        if child.dep_label == "obj":
            PAS["obja"] = child.lemma
            sub_pas = get_sub_pas(sent, child)
            if sub_pas == {} and sub_pas == []:
                pass
            elif isinstance(sub_pas, list) and sub_pas != []:
                for i, sub in enumerate(sub_pas, 1):
                    if sub.get("subj") is None:
                        sub["subj"] = PAS["subj"]
                        PAS["objc(obj){}".format(i)] = sub
                    else:
                        PAS["objc(obj){}".format(i)] = sub

        if child.dep_label == "obl" or child.dep_label == "nmod":
            if 'Case=Acc' in child.morph_feat:
                PAS["pp"] = child.lemma
            if 'Case=Dat' in child.morph_feat:
                PAS["objd"] = child.lemma
            if ('Case=Loc' in child.morph_feat):
                PAS["pp"] = child.lemma
            if ('Case=Gen' in child.morph_feat):
                PAS["pp"] = child.lemma
            if 'Case=Ins' in child.morph_feat:
                PAS["instr"] = child.lemma

            sub_pas = get_sub_pas(sent, child)
            if sub_pas == {} and sub_pas == []:
                pass
            elif isinstance(sub_pas, list) and sub_pas != []:
                for i, sub in enumerate(sub_pas, 1):
                    if sub.get("subj") is None and PAS.get("subj") is not None:
                        sub["subj"] = PAS["subj"]
                        PAS["objc(objl){}".format(i)] = sub
                    else:
                        PAS["objc(objl){}".format(i)] = sub

        if child.dep_label == "obl:passsubj":
            PAS["objl"] = child.lemma
            PAS["objl:passsubj"] = PAS.pop("objl")

    # for child in children:
        # if (child.dep_label == "obj") and (PAS.get("obja") is not None):
        #     PAS.pop('obja', None)
        if child.dep_label == "xcomp" or child.dep_label == "dep":
            sub_inf = get_sub_pas(sent, child)
            if sub_inf == {} or sub_inf == []:
                pass
            elif isinstance(sub_inf, list) and sub_inf != []:
                for i, inf in enumerate(sub_inf, 1):
                    if (PAS.get("subj") is not None) and (
                        PAS.get("objd") is None) and (
                            PAS.get("obja") is None):

                        inf["subj"] = PAS["subj"]
                        PAS["objc(inf){}".format(i)] = inf
                    elif (PAS.get("objd") is not None) and (
                            PAS.get("obja") is None):
                        inf["subj"] = PAS["objd"]
                        PAS["objc(inf){}".format(i)] = inf
                    elif (PAS.get("objd") is None) and (
                            PAS.get("obja") is not None):
                        inf["subj"] = PAS["obja"]
                        PAS["objc(inf){}".format(i)] = inf

            # PAS["objc(i)"] = "s2"
            # sub_inf["verb"] = child.lemma
            # if (PAS.get("objd") is None) and (
            #         PAS.get("subj") is not None):
            #     sub_inf["subj"] = PAS["subj"]
            #     print(PAS["subj"])
            # else:
            #     try:
            #         sub_inf["subj"] = PAS["objd"]
            #         try:
            #             sub_inf["subj"] = PAS["obja"]
            #         except KeyError:
            #             pass
            #     except KeyError:
            #         pass

            # inf_children = cso.get_children(sent, child)
            # sub_inf["neg"] = False
            # for inf_chi in inf_children:
            #     if inf_chi.dep_label == "obj":
            #         sub_inf["obja"] = inf_chi.lemma
            #     elif inf_chi.dep_label == "obl" and sub_inf.get("obja") is None:
            #         if 'Case=Acc' in child.morph_feat:
            #             PAS["pp"] = child.lemma
            #         elif 'Case=Dat' in child.morph_feat:
            #             PAS["objd"] = child.lemma
            #         elif ('Case=Loc' in child.morph_feat) or (
            #                 'Case=Gen' in child.morph_feat):
            #             PAS["pp"] = child.lemma
            #         elif 'Case=Ins' in child.morph_feat:
            #             PAS['instr'] in child.lemma
                # if inf_chi.lemma == "не":
                #     sub_inf["neg"] = True
            # sub_pas = get_sub_pas(sent, child)
            # if sub_pas == {} and sub_pas == []:
            #     pass
            # elif isinstance(sub_pas, list) and sub_pas != []:
            #     for i, sub in enumerate(sub_pas, 1):
            #         if sub.get("subj") is None and PAS.get("subj") is not None:
            #             sub["subj"] = sub_inf["subj"]
            #             PAS["objc(inf){}".format(i)] = sub
            #         else:
            #             PAS["objc(inf){}".format(i)] = sub

    sub_pas = get_sub_pas(sent, root)
    if sub_pas == {} or sub_pas == []:
        pass
    elif isinstance(sub_pas, list) and sub_pas != []:
        for i, sub in enumerate(sub_pas, 1):
            if sub.get("subj") is None:
                if (PAS.get("subj") is not None) and (
                    PAS.get("objd") is None) and (
                        PAS.get("obja") is None):

                    sub["subj"] = PAS["subj"]
                    PAS["objc{}".format(i)] = sub
                elif (PAS.get("objd") is not None) and (
                        PAS.get("obja") is None):
                    sub["subj"] = PAS["objd"]
                    PAS["objc{}".format(i)] = sub
                elif (PAS.get("objd") is None) and (
                        PAS.get("obja") is not None):
                    sub["subj"] = PAS["obja"]
                    PAS["obj){}".format(i)] = sub
            else:
                PAS["objc{}".format(i)] = sub
            # elif PAS.get("obja") is not None and PAS.get("objd") is None and PAS.get("subj") is None:
            #     # print(PAS["obja"])
            #     sub["subj"] = PAS["obja"]
            #     PAS["objc{}".format(i)] = sub
            # else:
            #     sub["subj"] = Subj()
            #     PAS["objc{}".format(i)] = sub

            # if sub.get("subj") is None and PAS.get("subj") is not None:
            #     sub["subj"] = PAS["subj"]
            #     PAS["objc{}".format(i)] = sub
            # else:
            #     PAS["objc{}".format(i)] = sub

    neg, passive = detect_neg_passive(sent, root)
    PAS["neg"] = neg
    PAS["passive"] = passive
    if passive is True:
        if PAS.get("subj") is not None:
            PAS["passobj"] = PAS.pop("subj")
        if PAS.get("obja") is not None:
            print(PAS)
            PAS["subj"] = PAS.pop("obja")
            PAS["obja"] = PAS.pop("passobj")
        if PAS.get("instr") is not None:
            PAS["subj"] = PAS.pop("instr")
            PAS["obja"] = PAS.pop("passobj")
        elif PAS.get("instr") is None:
            try:
                PAS["subj"] = PAS.pop("objl:passsubj")
                PAS["obja"] = PAS.pop("passobj")
            except KeyError:
                pass

    if "objc(i)" in PAS.keys():
        PAS["objc(i)"] = sub_inf

    return PAS


def get_PAS_with_verb(INPUT_CONLL, input_verb):
    '''define PAS of input .conll sentences from a given verb.
    Takes as arguments: 1) sentences in .CONLL format; 2) verb
    '''
    sentences = read_conll_with_cru(INPUT_CONLL)
    sent_id = read_conll_sent_ids(INPUT_CONLL)
    list_of_sent = []

    for sid, sent in zip(sent_id, sentences):
        PAS = {}
        sub_inf = {}
        verb = [token for token in sent.conll_tokens if token.lemma == input_verb][0]
        PAS["verb"] = verb.lemma

        children = cso.get_children(sent, verb)

        for child in children:
            if child.dep_label == "nsubj":
                PAS["subj"] = child.lemma
                sub_pas = get_sub_pas(sent, child)
                if sub_pas == {} and sub_pas == []:
                    pass
                elif isinstance(sub_pas, list) and sub_pas != []:
                    for i, sub in enumerate(sub_pas, 1):
                        if sub.get("subj") is None:
                            sub["subj"] = PAS["subj"]
                            PAS["objc(obj){}".format(i)] = sub
                        else:
                            PAS["objc(obj){}".format(i)] = sub

            if child.dep_label == "nsubj:pass" and PAS.get("subj") is None:
                PAS["subj"] = child.lemma
            if child.dep_label == "obj":
                PAS["obja"] = child.lemma
                sub_pas = get_sub_pas(sent, child)
                if sub_pas == {} or sub_pas == []:
                    pass
                elif isinstance(sub_pas, list) and sub_pas != []:
                    for i, sub in enumerate(sub_pas, 1):
                        if sub.get("subj") is None:
                            sub["subj"] = PAS["subj"]
                            PAS["objc(obj){}".format(i)] = sub
                        else:
                            PAS["objc(obj){}".format(i)] = sub

            if child.dep_label == "obl" and PAS.get("obja") is None:
                if 'Case=Acc' in child.morph_feat:
                    PAS["pp"] = child.lemma
                elif 'Case=Dat' in child.morph_feat:
                    PAS["objd"] = child.lemma
                elif ('Case=Loc' in child.morph_feat) or (
                        'Case=Gen' in child.morph_feat):
                    PAS["pp"] = child.lemma
                elif 'Case=Ins' in child.morph_feat:
                    PAS['instr'] in child.lemma

                sub_pas = get_sub_pas(sent, child)
                if sub_pas == {} and sub_pas == []:
                    pass
                elif isinstance(sub_pas, list) and sub_pas != []:
                    for i, sub in enumerate(sub_pas, 1):
                        if sub.get("subj") is None and PAS.get("subj") is not None:
                            sub["subj"] = PAS["subj"]
                            PAS["objc(objl){}".format(i)] = sub
                        else:
                            PAS["objc(objl){}".format(i)] = sub

            if child.dep_label == "obl:passsubj":
                PAS["objl"] = child.lemma
                PAS["objl:passsubj"] = PAS.pop("objl")

        for child in children:
            # if (child.dep_label == "obj") and (PAS.get("obja") is not None):
            #     PAS.pop('obja', None)
            if child.dep_label == "xcomp" or child.dep_label == "dep":
                PAS["objc(i)"] = "s2"
                sub_inf["verb"] = child.lemma
                if (PAS.get("objd") is None) and (PAS.get("obja") is None) and (
                        PAS.get("subj") is not None):
                    sub_inf["subj"] = PAS["subj"]
                else:
                    try:
                        sub_inf["subj"] = PAS["objd"]
                        try:
                            sub_inf["subj"] = PAS["obja"]
                        except KeyError:
                            pass
                    except KeyError:
                        pass

                inf_children = cso.get_children(sent, child)
                sub_inf["neg"] = False
                for inf_chi in inf_children:
                    if inf_chi.dep_label == "obj":
                        sub_inf["obja"] = inf_chi.lemma
                    elif inf_chi.dep_label == "obl" and sub_inf.get("obja") is None:
                        if 'Case=Acc' in child.morph_feat:
                            PAS["pp"] = child.lemma
                        elif 'Case=Dat' in child.morph_feat:
                            PAS["objd"] = child.lemma
                        elif ('Case=Loc' in child.morph_feat) or (
                                'Case=Gen' in child.morph_feat):
                            PAS["pp"] = child.lemma
                        elif 'Case=Ins' in child.morph_feat:
                            PAS['instr'] in child.lemma
                    if inf_chi.lemma == "не":
                        sub_inf["neg"] = True
                sub_pas = get_sub_pas(sent, child)
                if sub_pas == {} and sub_pas == []:
                    pass
                elif isinstance(sub_pas, list) and sub_pas != []:
                    for i, sub in enumerate(sub_pas, 1):
                        if sub.get("subj") is None and PAS.get("subj") is not None:
                            sub["subj"] = sub_inf["subj"]
                            PAS["objc(inf){}".format(i)] = sub
                        else:
                            PAS["objc(inf){}".format(i)] = sub

        sub_pas = get_sub_pas(sent, root)
        if sub_pas == {} and sub_pas == []:
            pass
        elif isinstance(sub_pas, list) and sub_pas != []:
            for i, sub in enumerate(sub_pas, 1):
                if sub.get("subj") is None and PAS.get("subj") is not None:
                    sub["subj"] = PAS["subj"]
                    PAS["objc{}".format(i)] = sub
                else:
                    PAS["objc{}".format(i)] = sub

        neg, passive = detect_neg_passive(sent, root)
        PAS["neg"] = neg
        PAS["passive"] = passive
        if passive is True:
            if PAS.get("subj") is not None:
                PAS["passobj"] = PAS.pop("subj")
            if PAS.get("obja") is not None:
                PAS["passsubj"] = PAS.pop("obja")
            if PAS.get("instr") is not None:
                PAS["passsubj"] = PAS.pop("instr")
            elif PAS.get("instr") is None:
                try:
                    PAS["passsubj"] = PAS.pop("objl:passsubj")
                except KeyError:
                    pass

        if "objc(i)" in PAS.keys():
            PAS["objc(i)"] = sub_inf

        # add sentence ID
        sentence = {
            "sent_id": int(sid.split(" = ")[-1]),
            "PAS": PAS
        }

        list_of_sent.append(sentence)

        # list_of_sent.append(PAS)
    write_results_into_outfile(list_of_sent)

    return list_of_sent


def detect_neg_passive(sentence, verb):
    '''define wheither a sentence is either negative or positive and
    either passive or active '''
    # _json_tree = build_json_tree(sentence)
    negation = False
    passive = False
    verb_children = cso.get_children(sentence, verb)
    for token in verb_children:
        if "не" == token.lemma or "вряд" == token.lemma:
            negation = True

    for token in sentence.conll_tokens:
        if verb.lemma in token.lemma:
            if "Voice=Pass" in token.morph_feat:
                passive = True

    return negation, passive


def get_sub_pas(sentence, parent_element):
    '''get PAS of a suborbinate clause with its possible parent element.
    Takes as arguments: 1) a sentence in .CONLL format; 2) a parent element
    '''
    sub_clause_labels = ["advcl", "acl:relcl", "ccomp", "conj", "parataxis", "xcomp", "dep"]
    sub_pas = []
    children = cso.get_children(sentence, parent_element)

    for child in children:
        if child.C_pos_tag == "NOUN" and parent_element.C_pos_tag == "NOUN":
            sub_pas = []
            # return sub_pas

        elif child.dep_label in sub_clause_labels and (
            child.C_pos_tag == "VERB" or child.C_pos_tag == "ADJ" or child.C_pos_tag == "NOUN"):
            pas = get_PAS(sentence, child)
            sub_pas.append(pas)

        # elif child.dep_label == "obl" and (child.C_pos_tag == "NOUN"):
        #     # print(child)
        #     pas = get_PAS(sentence, child)
        #     # print(pas)
        #     sub_pas.append(pas)

        # elif child.dep_label == "obj" and (child.C_pos_tag == "NOUN"):
        #     pas = get_PAS(sentence, child)
        #     sub_pas.append(pas)

    return sub_pas


def write_results_into_outfile(results):
    with open(OUTPUT_PAS, "a", encoding="utf-8") as outfile:
        # for sent in results:
        #     outfile.writelines(str(sent))
        #     outfile.writelines("\n")
        json.dump(results, outfile)

# NEXT FUNCTIONS WERE SUPPOSED TO BE USED FOR THE FULL GRAMMAR TREE

# def fix_passive_pas(INPUT_CONLL, key='passive'):
#     parsed_sentences = turn_conll_to_json(INPUT_CONLL)

#     for sent in parsed_sentences:
#         passive_bool = find_by_key(sent, key)
#         if passive_bool is True:
#             passive_sent = rename_by_key(sent, "nsubj", "obja")
#             # print("Passive is TRUE")
#             # print(sent)

#     return passive_sent


# def find_by_key(dictionary, key):
#     ''' returns a value by key in nested structure
#     '''
#     for k, v in dictionary.items():
#         if k == key:
#             return v
#         elif isinstance(v, dict):
#             result = find_by_key(v, key)

#             return result


# def rename_by_key(dictionary, oldkey, newkey):
#     '''change old key into the new one in the dictionary
#     '''
#     # print(dictionary)
#     for k, v in dictionary.items():
#         if k == oldkey:
#             print(dictionary[k])
#             if isinstance(v, dict):
#                 v[newkey] = v.pop(k)
#             elif isinstance(v, list):
#                 v[newkey] = v[0].pop(k)
#             return v
#         elif isinstance(v, dict):
#             # print(v)
#             result = rename_by_key(v, oldkey, newkey)
#             return dictionary
#         elif isinstance(v, list):
#             # print(v)
#             check_all = None
#             for d in v:
#                 # print(d)
#                 result = rename_by_key(d, oldkey, newkey)
#                 if result is None:
#                     pass
#                 else:
#                     check_all = result
#             return dictionary

def main():
    # print(read_conll(INPUT_CONLL))
    # print(read_conll_with_cru(INPUT_CONLL))

    # print(turn_conll_to_json(INPUT_CONLL))

    print(build_full_PAS(INPUT_CONLL))

    # print(get_PAS(INPUT_CONLL))
    # print(get_PAS_with_verb(INPUT_CONLL, "озадачивать"))
    # print(get_PAS_with_verb(INPUT_CONLL, "принуждать"))
    # print(fix_passive_pas(INPUT_CONLL))


if __name__ == "__main__":
    main()
