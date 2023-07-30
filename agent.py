"""The brain."""


import numpy as np
import torch
import torch.nn as nn
from torch.distributions.normal import Normal


def layer_init(layer, std=np.sqrt(2), bias_const=0.0):
    torch.nn.init.orthogonal_(layer.weight, std)
    torch.nn.init.constant_(layer.bias, bias_const)
    return layer


class Agent(nn.Module):
    def __init__(self, device, envs, rpo_alpha=0.5, enjoy=False):
        super().__init__()
        self.device = device
        self.rpo_alpha = rpo_alpha
        self.enjoy = enjoy
        self.critic = nn.Sequential(
            layer_init(nn.Linear(
                np.array(envs.single_observation_space.shape).prod(),
                512)),
            nn.Tanh(),
            layer_init(nn.Linear(512, 512)),
            nn.Tanh(),
            layer_init(nn.Linear(512, 1), std=1.0),
        )
        self.actor_mean = nn.Sequential(
            layer_init(nn.Linear(
                np.array(envs.single_observation_space.shape).prod(),
                512)),
            nn.Tanh(),
            layer_init(nn.Linear(512, 512)),
            nn.Tanh(),
            layer_init(
                nn.Linear(512,
                np.prod(envs.single_action_space.shape)), std=0.01),
        )
        self.actor_logstd = nn.Parameter(
            torch.zeros(1, np.prod(envs.single_action_space.shape)))

    def get_value(self, x):
        return self.critic(x)

    def get_action_and_value(self, x, action=None):
        action_mean = self.actor_mean(x)
        action_logstd = self.actor_logstd.expand_as(action_mean)
        action_std = torch.exp(action_logstd)
        probs = Normal(action_mean, action_std)
        if action is None:
            if self.enjoy:  # We need enjoy for rendering
                action = probs.mean
            else:
                action = probs.sample()
        else:  # new to RPO
            # sample again to add stochasticity to the policy
            z = torch.FloatTensor(action_mean.shape).uniform_(
                -self.rpo_alpha, self.rpo_alpha).to(self.device)
            action_mean = action_mean + z
            probs = Normal(action_mean, action_std)

        return action, probs.log_prob(action).sum(
            1), probs.entropy().sum(1), self.critic(x)
