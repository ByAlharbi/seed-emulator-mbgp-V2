#!/bin/bash

[ ! -d /run/bird ] && mkdir /run/bird
bird -d
