#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { TelegramBotStack } from '../lib/telegram-bot-stack';

const app = new cdk.App();
new TelegramBotStack(app, 'TelegramBotStack', {
  env: {
    region: 'us-east-1',
  },
});